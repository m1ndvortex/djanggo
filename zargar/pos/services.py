"""
Point of Sale (POS) services for ZARGAR jewelry SaaS platform.
Provides transaction processing, gold price calculations, and offline synchronization.
"""
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .models import POSTransaction, POSTransactionLineItem, POSInvoice, POSOfflineStorage
from zargar.jewelry.models import JewelryItem
from zargar.customers.models import Customer
from zargar.gold_installments.services import GoldPriceService
from django.db import models

logger = logging.getLogger(__name__)
User = get_user_model()


class POSTransactionService:
    """
    Service for processing POS transactions with gold price calculations.
    Handles both online and offline transaction processing.
    """
    
    @classmethod
    def create_transaction(cls, customer_id: Optional[int] = None,
                          transaction_type: str = 'sale',
                          payment_method: str = 'cash',
                          user: Optional[User] = None) -> POSTransaction:
        """
        Create a new POS transaction.
        
        Args:
            customer_id: Customer ID (optional for walk-in customers)
            transaction_type: Type of transaction
            payment_method: Payment method
            user: User creating the transaction
            
        Returns:
            Created POSTransaction instance
        """
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                raise ValidationError(f"Customer with ID {customer_id} not found")
        
        # Get current gold price for reference
        gold_price_data = GoldPriceService.get_current_gold_price(18)
        
        pos_transaction = POSTransaction.objects.create(
            customer=customer,
            transaction_type=transaction_type,
            payment_method=payment_method,
            gold_price_18k_at_transaction=gold_price_data['price_per_gram'],
            created_by=user
        )
        
        logger.info(f"Created POS transaction {pos_transaction.transaction_number}")
        return pos_transaction
    
    @classmethod
    def add_jewelry_item_to_transaction(cls, transaction: POSTransaction,
                                       jewelry_item_id: int,
                                       quantity: int = 1,
                                       custom_price: Optional[Decimal] = None,
                                       discount_percentage: Decimal = Decimal('0.00')) -> POSTransactionLineItem:
        """
        Add a jewelry item to POS transaction.
        
        Args:
            transaction: POSTransaction instance
            jewelry_item_id: JewelryItem ID
            quantity: Item quantity
            custom_price: Custom price override
            discount_percentage: Discount percentage to apply
            
        Returns:
            Created POSTransactionLineItem instance
        """
        try:
            jewelry_item = JewelryItem.objects.get(id=jewelry_item_id)
        except JewelryItem.DoesNotExist:
            raise ValidationError(f"Jewelry item with ID {jewelry_item_id} not found")
        
        # Check inventory availability
        if jewelry_item.quantity < quantity:
            raise ValidationError(f"Insufficient inventory. Available: {jewelry_item.quantity}, Requested: {quantity}")
        
        # Calculate price
        if custom_price is not None:
            unit_price = custom_price
        else:
            unit_price = cls._calculate_jewelry_item_price(jewelry_item, transaction.gold_price_18k_at_transaction)
        
        # Create line item
        line_item = POSTransactionLineItem.objects.create(
            transaction=transaction,
            jewelry_item=jewelry_item,
            item_name=jewelry_item.name,
            item_sku=jewelry_item.sku,
            quantity=quantity,
            unit_price=unit_price,
            gold_weight_grams=jewelry_item.weight_grams * quantity if jewelry_item.weight_grams else Decimal('0.000'),
            gold_karat=jewelry_item.karat,
            gold_price_per_gram_at_sale=transaction.gold_price_18k_at_transaction
        )
        
        # Apply discount if specified
        if discount_percentage > 0:
            line_item.apply_discount(discount_percentage=discount_percentage)
        
        # Recalculate transaction totals
        transaction.calculate_totals()
        transaction.save(update_fields=['subtotal', 'total_amount', 'total_gold_weight_grams'])
        
        logger.info(f"Added jewelry item {jewelry_item.sku} to transaction {transaction.transaction_number}")
        return line_item
    
    @classmethod
    def add_custom_item_to_transaction(cls, transaction: POSTransaction,
                                      item_name: str,
                                      unit_price: Decimal,
                                      quantity: int = 1,
                                      item_sku: str = '',
                                      gold_weight_grams: Optional[Decimal] = None,
                                      gold_karat: Optional[int] = None) -> POSTransactionLineItem:
        """
        Add a custom item to POS transaction.
        
        Args:
            transaction: POSTransaction instance
            item_name: Custom item name
            unit_price: Item price
            quantity: Item quantity
            item_sku: Item SKU (optional)
            gold_weight_grams: Gold weight if applicable
            gold_karat: Gold karat if applicable
            
        Returns:
            Created POSTransactionLineItem instance
        """
        line_item = POSTransactionLineItem.objects.create(
            transaction=transaction,
            item_name=item_name,
            item_sku=item_sku,
            quantity=quantity,
            unit_price=unit_price,
            gold_weight_grams=gold_weight_grams or Decimal('0.000'),
            gold_karat=gold_karat or 0,
            gold_price_per_gram_at_sale=transaction.gold_price_18k_at_transaction
        )
        
        # Recalculate transaction totals
        transaction.calculate_totals()
        transaction.save(update_fields=['subtotal', 'total_amount', 'total_gold_weight_grams'])
        
        logger.info(f"Added custom item '{item_name}' to transaction {transaction.transaction_number}")
        return line_item
    
    @classmethod
    def remove_line_item(cls, transaction: POSTransaction, line_item_id: int):
        """
        Remove a line item from transaction.
        
        Args:
            transaction: POSTransaction instance
            line_item_id: Line item ID to remove
        """
        try:
            line_item = transaction.line_items.get(id=line_item_id)
            line_item.delete()
            
            # Recalculate transaction totals
            transaction.calculate_totals()
            transaction.save(update_fields=['subtotal', 'total_amount', 'total_gold_weight_grams'])
            
            logger.info(f"Removed line item {line_item_id} from transaction {transaction.transaction_number}")
            
        except POSTransactionLineItem.DoesNotExist:
            raise ValidationError(f"Line item with ID {line_item_id} not found")
    
    @classmethod
    def apply_transaction_discount(cls, transaction: POSTransaction,
                                  discount_amount: Decimal):
        """
        Apply discount to entire transaction.
        
        Args:
            transaction: POSTransaction instance
            discount_amount: Discount amount in Toman
        """
        transaction.discount_amount = discount_amount
        transaction.calculate_totals()
        transaction.save(update_fields=['discount_amount', 'total_amount'])
        
        logger.info(f"Applied discount of {discount_amount} Toman to transaction {transaction.transaction_number}")
    
    @classmethod
    def calculate_tax(cls, transaction: POSTransaction, tax_rate: Decimal = Decimal('9.00')) -> Decimal:
        """
        Calculate tax for transaction (Iranian VAT is typically 9%).
        
        Args:
            transaction: POSTransaction instance
            tax_rate: Tax rate percentage
            
        Returns:
            Calculated tax amount
        """
        tax_amount = (transaction.subtotal * tax_rate / 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        transaction.tax_amount = tax_amount
        transaction.calculate_totals()
        transaction.save(update_fields=['tax_amount', 'total_amount'])
        
        return tax_amount
    
    @classmethod
    def process_payment(cls, transaction: POSTransaction,
                       amount_paid: Decimal,
                       payment_method: Optional[str] = None,
                       reference_number: str = '') -> Dict:
        """
        Process payment for POS transaction.
        
        Args:
            transaction: POSTransaction instance
            amount_paid: Amount paid by customer
            payment_method: Payment method (optional, uses transaction default)
            reference_number: Payment reference number
            
        Returns:
            Dictionary with payment processing results
        """
        if payment_method:
            transaction.payment_method = payment_method
        
        transaction.amount_paid = amount_paid
        transaction.reference_number = reference_number
        
        # Validate payment amount
        if amount_paid < transaction.total_amount:
            raise ValidationError(f"Insufficient payment. Required: {transaction.total_amount}, Paid: {amount_paid}")
        
        # Calculate change
        transaction.calculate_totals()
        
        try:
            from django.db import transaction as db_transaction
            
            with db_transaction.atomic():
                # Complete the transaction
                transaction.complete_transaction()
                
                # Create invoice
                invoice = cls._create_invoice(transaction)
                
                logger.info(f"Processed payment for transaction {transaction.transaction_number}: "
                           f"{amount_paid} Toman, Change: {transaction.change_amount} Toman")
                
                return {
                    'success': True,
                    'transaction': transaction,
                    'invoice': invoice,
                    'change_amount': transaction.change_amount,
                    'payment_successful': True
                }
                
        except Exception as e:
            logger.error(f"Error processing payment for transaction {transaction.transaction_number}: {e}")
            raise ValidationError(f"Payment processing failed: {str(e)}")
    
    @classmethod
    def _calculate_jewelry_item_price(cls, jewelry_item: JewelryItem, 
                                     current_gold_price: Decimal) -> Decimal:
        """
        Calculate jewelry item price based on current gold price.
        
        Args:
            jewelry_item: JewelryItem instance
            current_gold_price: Current gold price per gram
            
        Returns:
            Calculated item price
        """
        # Use selling price if available
        if jewelry_item.selling_price:
            return jewelry_item.selling_price
        
        # Calculate based on gold value + manufacturing cost
        gold_value = Decimal('0.00')
        if jewelry_item.weight_grams and jewelry_item.karat and current_gold_price:
            gold_value = jewelry_item.calculate_gold_value(current_gold_price)
        
        manufacturing_cost = jewelry_item.manufacturing_cost or Decimal('0.00')
        gemstone_value = jewelry_item.gemstone_value or Decimal('0.00')
        
        total_price = gold_value + manufacturing_cost + gemstone_value
        
        # Add markup (e.g., 20%)
        markup_percentage = Decimal('20.00')  # This could be configurable
        markup_amount = total_price * (markup_percentage / 100)
        
        final_price = (total_price + markup_amount).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return final_price
    
    @classmethod
    def _create_invoice(cls, transaction: POSTransaction) -> POSInvoice:
        """
        Create invoice for completed transaction.
        
        Args:
            transaction: Completed POSTransaction instance
            
        Returns:
            Created POSInvoice instance
        """
        invoice = POSInvoice.objects.create(
            transaction=transaction,
            invoice_type='sale' if transaction.transaction_type == 'sale' else 'return',
            status='issued'
        )
        
        logger.info(f"Created invoice {invoice.invoice_number} for transaction {transaction.transaction_number}")
        return invoice
    
    @classmethod
    def cancel_transaction(cls, transaction: POSTransaction, reason: str = '') -> Dict:
        """
        Cancel a POS transaction.
        
        Args:
            transaction: POSTransaction instance
            reason: Cancellation reason
            
        Returns:
            Dictionary with cancellation results
        """
        if transaction.status == 'completed':
            raise ValidationError("Cannot cancel completed transaction")
        
        transaction.cancel_transaction(reason)
        
        logger.info(f"Cancelled transaction {transaction.transaction_number}: {reason}")
        
        return {
            'success': True,
            'transaction': transaction,
            'cancelled': True,
            'reason': reason
        }


class POSOfflineService:
    """
    Service for handling offline POS operations and synchronization.
    Manages local storage and sync when connection is restored.
    """
    
    @classmethod
    def store_offline_transaction(cls, transaction_data: Dict, device_id: str = '') -> POSOfflineStorage:
        """
        Store transaction data for offline processing.
        
        Args:
            transaction_data: Complete transaction data
            device_id: Device identifier
            
        Returns:
            Created POSOfflineStorage instance
        """
        offline_storage = POSOfflineStorage.objects.create(
            transaction_data=transaction_data,
            device_id=device_id
        )
        
        logger.info(f"Stored offline transaction {offline_storage.storage_id}")
        return offline_storage
    
    @classmethod
    def sync_offline_transactions(cls, device_id: Optional[str] = None) -> Dict:
        """
        Sync all pending offline transactions.
        
        Args:
            device_id: Specific device ID to sync (optional)
            
        Returns:
            Dictionary with sync results
        """
        # Get pending offline transactions
        queryset = POSOfflineStorage.objects.filter(is_synced=False)
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        offline_transactions = queryset.order_by('created_at')
        
        sync_results = {
            'total_pending': offline_transactions.count(),
            'synced_successfully': 0,
            'sync_failed': 0,
            'errors': []
        }
        
        for offline_transaction in offline_transactions:
            try:
                success = offline_transaction.sync_to_database()
                if success:
                    sync_results['synced_successfully'] += 1
                    logger.info(f"Successfully synced offline transaction {offline_transaction.storage_id}")
                else:
                    sync_results['sync_failed'] += 1
                    sync_results['errors'].append({
                        'storage_id': str(offline_transaction.storage_id),
                        'error': offline_transaction.sync_error
                    })
                    
            except Exception as e:
                sync_results['sync_failed'] += 1
                sync_results['errors'].append({
                    'storage_id': str(offline_transaction.storage_id),
                    'error': str(e)
                })
                logger.error(f"Failed to sync offline transaction {offline_transaction.storage_id}: {e}")
        
        logger.info(f"Offline sync completed: {sync_results['synced_successfully']} successful, "
                   f"{sync_results['sync_failed']} failed")
        
        return sync_results
    
    @classmethod
    def create_offline_transaction_data(cls, customer_id: Optional[int],
                                       line_items: List[Dict],
                                       payment_method: str,
                                       amount_paid: Decimal,
                                       transaction_type: str = 'sale') -> Dict:
        """
        Create offline transaction data structure.
        
        Args:
            customer_id: Customer ID (optional)
            line_items: List of line item dictionaries
            payment_method: Payment method
            amount_paid: Amount paid
            transaction_type: Transaction type
            
        Returns:
            Offline transaction data dictionary
        """
        import uuid
        
        # Get current gold price
        gold_price_data = GoldPriceService.get_current_gold_price(18)
        
        # Calculate totals
        subtotal = sum(
            Decimal(str(item['unit_price'])) * int(item['quantity']) 
            for item in line_items
        )
        
        transaction_data = {
            'transaction_id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'transaction_date': timezone.now().isoformat(),
            'transaction_type': transaction_type,
            'payment_method': payment_method,
            'subtotal': str(subtotal),
            'tax_amount': '0.00',  # Can be calculated later
            'discount_amount': '0.00',
            'total_amount': str(subtotal),
            'amount_paid': str(amount_paid),
            'gold_price_18k_at_transaction': str(gold_price_data['price_per_gram']),
            'line_items': line_items,
            'offline_created_at': timezone.now().isoformat()
        }
        
        return transaction_data
    
    @classmethod
    def get_offline_transaction_summary(cls, device_id: Optional[str] = None) -> Dict:
        """
        Get summary of offline transactions.
        
        Args:
            device_id: Specific device ID (optional)
            
        Returns:
            Dictionary with offline transaction summary
        """
        queryset = POSOfflineStorage.objects.all()
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        total_count = queryset.count()
        pending_count = queryset.filter(is_synced=False).count()
        synced_count = queryset.filter(is_synced=True).count()
        
        # Calculate total value of pending transactions
        pending_transactions = queryset.filter(is_synced=False)
        total_pending_value = Decimal('0.00')
        
        for offline_transaction in pending_transactions:
            try:
                data = offline_transaction.transaction_data
                total_pending_value += Decimal(data.get('total_amount', '0.00'))
            except (ValueError, KeyError):
                continue
        
        return {
            'total_transactions': total_count,
            'pending_sync': pending_count,
            'synced': synced_count,
            'total_pending_value': total_pending_value,
            'oldest_pending': pending_transactions.order_by('created_at').first().created_at if pending_count > 0 else None
        }


class POSInvoiceService:
    """
    Service for managing POS invoices with Persian formatting and Iranian compliance.
    """
    
    @classmethod
    def generate_invoice_pdf(cls, invoice: POSInvoice) -> bytes:
        """
        Generate PDF invoice with Persian formatting and Iranian business law compliance.
        
        Args:
            invoice: POSInvoice instance
            
        Returns:
            PDF content as bytes
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from io import BytesIO
            import os
            
            # Register Persian font (you would need to add Persian font files)
            # For now, using default fonts
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                                  topMargin=72, bottomMargin=18)
            
            # Get invoice data
            invoice_data = invoice.generate_persian_invoice_data()
            
            # Build PDF content
            story = []
            styles = getSampleStyleSheet()
            
            # Create RTL style for Persian text
            rtl_style = ParagraphStyle(
                'RTL',
                parent=styles['Normal'],
                alignment=2,  # Right alignment for RTL
                fontName='Helvetica',
                fontSize=12,
                leading=14
            )
            
            # Header - Business Information
            business_info = invoice_data['business_info']
            story.append(Paragraph(f"<b>{business_info['name']}</b>", rtl_style))
            story.append(Paragraph(business_info['address'], rtl_style))
            story.append(Paragraph(f"تلفن: {business_info['phone']}", rtl_style))
            if business_info['tax_id']:
                story.append(Paragraph(f"شناسه مالیاتی: {business_info['tax_id']}", rtl_style))
            story.append(Spacer(1, 12))
            
            # Invoice Header
            invoice_details = invoice_data['invoice_details']
            story.append(Paragraph(f"<b>فاکتور فروش - شماره: {invoice_details['invoice_number']}</b>", rtl_style))
            story.append(Paragraph(f"تاریخ صدور: {invoice_details['issue_date_shamsi']}", rtl_style))
            story.append(Spacer(1, 12))
            
            # Customer Information
            customer_info = invoice_data['customer_info']
            story.append(Paragraph("<b>مشخصات خریدار:</b>", rtl_style))
            story.append(Paragraph(f"نام: {customer_info['name']}", rtl_style))
            if customer_info['phone']:
                story.append(Paragraph(f"تلفن: {customer_info['phone']}", rtl_style))
            if customer_info['address']:
                story.append(Paragraph(f"آدرس: {customer_info['address']}", rtl_style))
            story.append(Spacer(1, 12))
            
            # Line Items Table
            table_data = [
                ['مجموع', 'قیمت واحد', 'تعداد', 'وزن (گرم)', 'کد کالا', 'شرح کالا']
            ]
            
            for item in invoice_data['line_items']:
                table_data.append([
                    item['line_total'],
                    item['unit_price'],
                    item['quantity'],
                    item['gold_weight'] or '-',
                    item['sku'] or '-',
                    item['name']
                ])
            
            # Create table
            table = Table(table_data, colWidths=[1*inch, 1*inch, 0.8*inch, 1*inch, 1*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            story.append(Spacer(1, 12))
            
            # Financial Totals
            financial_totals = invoice_data['financial_totals']
            story.append(Paragraph(f"جمع کل: {financial_totals['subtotal']}", rtl_style))
            if financial_totals['tax_amount'] != '۰':
                story.append(Paragraph(f"مالیات: {financial_totals['tax_amount']}", rtl_style))
            if financial_totals['discount_amount'] != '۰':
                story.append(Paragraph(f"تخفیف: {financial_totals['discount_amount']}", rtl_style))
            story.append(Paragraph(f"<b>مبلغ نهایی: {financial_totals['total_amount']}</b>", rtl_style))
            story.append(Paragraph(f"به حروف: {financial_totals['total_in_words']}", rtl_style))
            story.append(Spacer(1, 12))
            
            # Terms and Conditions
            if invoice_data['terms_and_conditions']:
                story.append(Paragraph("<b>شرایط و ضوابط:</b>", rtl_style))
                story.append(Paragraph(invoice_data['terms_and_conditions'], rtl_style))
            
            # Notes
            if invoice_data['notes']:
                story.append(Spacer(1, 12))
                story.append(Paragraph("<b>توضیحات:</b>", rtl_style))
                story.append(Paragraph(invoice_data['notes'], rtl_style))
            
            # Build PDF
            doc.build(story)
            
            pdf_content = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Generated PDF for invoice {invoice.invoice_number}")
            return pdf_content
            
        except ImportError:
            # Fallback if ReportLab is not available
            logger.warning("ReportLab not available, generating simple PDF placeholder")
            return cls._generate_simple_pdf_placeholder(invoice)
        except Exception as e:
            logger.error(f"Error generating PDF for invoice {invoice.invoice_number}: {e}")
            return cls._generate_simple_pdf_placeholder(invoice)
    
    @classmethod
    def _generate_simple_pdf_placeholder(cls, invoice: POSInvoice) -> bytes:
        """
        Generate a simple PDF placeholder when ReportLab is not available.
        
        Args:
            invoice: POSInvoice instance
            
        Returns:
            Simple PDF content as bytes
        """
        # Simple text-based PDF content
        invoice_data = invoice.generate_persian_invoice_data()
        
        content = f"""
        فاکتور فروش
        شماره فاکتور: {invoice_data['invoice_details']['invoice_number']}
        تاریخ: {invoice_data['invoice_details']['issue_date_shamsi']}
        
        مشخصات فروشنده:
        {invoice_data['business_info']['name']}
        {invoice_data['business_info']['address']}
        تلفن: {invoice_data['business_info']['phone']}
        
        مشخصات خریدار:
        نام: {invoice_data['customer_info']['name']}
        تلفن: {invoice_data['customer_info']['phone']}
        
        اقلام:
        """
        
        for item in invoice_data['line_items']:
            content += f"\n{item['name']} - تعداد: {item['quantity']} - قیمت: {item['line_total']}"
        
        content += f"""
        
        جمع کل: {invoice_data['financial_totals']['total_amount']}
        به حروف: {invoice_data['financial_totals']['total_in_words']}
        """
        
        # Convert to bytes (this is a simplified approach)
        return content.encode('utf-8')
    
    @classmethod
    def generate_invoice_for_transaction(cls, transaction: POSTransaction,
                                       invoice_type: str = 'sale',
                                       auto_issue: bool = True) -> POSInvoice:
        """
        Generate invoice for a completed transaction with automatic gold price calculation.
        
        Args:
            transaction: Completed POSTransaction instance
            invoice_type: Type of invoice ('sale', 'return', 'proforma')
            auto_issue: Whether to automatically mark invoice as issued
            
        Returns:
            Created POSInvoice instance
        """
        if transaction.status != 'completed':
            raise ValidationError("Cannot generate invoice for incomplete transaction")
        
        # Check if invoice already exists
        if hasattr(transaction, 'invoice'):
            return transaction.invoice
        
        # Create invoice
        invoice = POSInvoice.objects.create(
            transaction=transaction,
            invoice_type=invoice_type,
            status='issued' if auto_issue else 'draft'
        )
        
        # Set Iranian business compliance fields if available
        if hasattr(transaction, 'tenant') and transaction.tenant:
            # Get tenant business information
            tenant = transaction.tenant
            if hasattr(tenant, 'tax_id'):
                invoice.tax_id = tenant.tax_id
            if hasattr(tenant, 'economic_code'):
                invoice.economic_code = tenant.economic_code
        
        logger.info(f"Generated invoice {invoice.invoice_number} for transaction {transaction.transaction_number}")
        return invoice
    
    @classmethod
    def send_invoice_email(cls, invoice: POSInvoice, recipient_email: str,
                          include_pdf: bool = True) -> bool:
        """
        Send invoice via email with Persian template.
        
        Args:
            invoice: POSInvoice instance
            recipient_email: Recipient email address
            include_pdf: Whether to include PDF attachment
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Generate invoice data
            invoice_data = invoice.generate_persian_invoice_data()
            
            # TODO: Implement email sending with Persian template
            # This would integrate with Iranian email services
            
            # Generate PDF if requested
            pdf_content = None
            if include_pdf:
                pdf_content = cls.generate_invoice_pdf(invoice)
            
            # Send email (placeholder implementation)
            success = invoice.send_email(recipient_email)
            
            if success:
                logger.info(f"Sent invoice {invoice.invoice_number} to {recipient_email}")
            else:
                logger.error(f"Failed to send invoice {invoice.invoice_number} to {recipient_email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending invoice email: {e}")
            return False
    
    @classmethod
    def get_invoice_template_data(cls, invoice: POSInvoice) -> Dict:
        """
        Get invoice data formatted for template rendering.
        
        Args:
            invoice: POSInvoice instance
            
        Returns:
            Dictionary with template data
        """
        return invoice.generate_persian_invoice_data()


class POSCustomerService:
    """
    Service for customer lookup and credit/debt management in POS system.
    """
    
    @classmethod
    def search_customers(cls, query: str, limit: int = 20) -> List[Dict]:
        """
        Search customers by name, phone, or email with Persian support.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of customer dictionaries with relevant information
        """
        if len(query.strip()) < 2:
            return []
        
        # Search in multiple fields with Persian support
        customers = Customer.objects.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(persian_first_name__icontains=query) |
            models.Q(persian_last_name__icontains=query) |
            models.Q(phone_number__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(national_id__icontains=query),
            is_active=True
        ).select_related().order_by('-last_purchase_date', '-total_purchases')[:limit]
        
        customer_data = []
        for customer in customers:
            # Calculate current balance (credit/debt)
            balance_info = cls.get_customer_balance(customer)
            
            customer_data.append({
                'id': customer.id,
                'name': str(customer),
                'full_persian_name': customer.full_persian_name,
                'phone_number': customer.phone_number,
                'email': customer.email or '',
                'customer_type': customer.get_customer_type_display(),
                'is_vip': customer.is_vip,
                'loyalty_points': customer.loyalty_points,
                'total_purchases': float(customer.total_purchases),
                'last_purchase_date': customer.last_purchase_date.isoformat() if customer.last_purchase_date else None,
                'balance_info': balance_info,
                'is_birthday_today': customer.is_birthday_today,
            })
        
        return customer_data
    
    @classmethod
    def get_customer_balance(cls, customer: Customer) -> Dict:
        """
        Calculate customer's current credit/debt balance from all transactions.
        
        Args:
            customer: Customer instance
            
        Returns:
            Dictionary with balance information
        """
        from decimal import Decimal
        
        # Get all completed transactions for this customer
        transactions = POSTransaction.objects.filter(
            customer=customer,
            status='completed'
        )
        
        total_purchases = Decimal('0.00')
        total_payments = Decimal('0.00')
        total_returns = Decimal('0.00')
        
        for transaction in transactions:
            if transaction.transaction_type == 'sale':
                total_purchases += transaction.total_amount
                total_payments += transaction.amount_paid
            elif transaction.transaction_type == 'return':
                total_returns += transaction.total_amount
        
        # Calculate balance
        # Positive balance = customer owes money (debt)
        # Negative balance = shop owes money to customer (credit)
        balance = total_purchases - total_payments - total_returns
        
        # Get installment balances if any
        installment_balance = cls._get_customer_installment_balance(customer)
        
        return {
            'current_balance': float(balance),
            'balance_type': 'debt' if balance > 0 else 'credit' if balance < 0 else 'zero',
            'total_purchases': float(total_purchases),
            'total_payments': float(total_payments),
            'total_returns': float(total_returns),
            'installment_balance': installment_balance,
            'formatted_balance': cls._format_balance_display(balance),
        }
    
    @classmethod
    def _get_customer_installment_balance(cls, customer: Customer) -> Dict:
        """
        Get customer's gold installment balance if any.
        
        Args:
            customer: Customer instance
            
        Returns:
            Dictionary with installment balance information
        """
        try:
            from zargar.gold_installments.models import GoldInstallmentContract
            
            active_contracts = GoldInstallmentContract.objects.filter(
                customer=customer,
                status='active'
            )
            
            total_gold_debt = Decimal('0.000')
            total_toman_value = Decimal('0.00')
            contract_count = active_contracts.count()
            
            for contract in active_contracts:
                total_gold_debt += contract.remaining_gold_weight
                # Calculate current Toman value
                current_gold_price = GoldPriceService.get_current_gold_price(18)
                total_toman_value += contract.remaining_gold_weight * current_gold_price['price_per_gram']
            
            return {
                'has_installments': contract_count > 0,
                'contract_count': contract_count,
                'total_gold_debt_grams': float(total_gold_debt),
                'current_toman_value': float(total_toman_value),
                'formatted_gold_debt': f"{total_gold_debt:.3f} گرم" if total_gold_debt > 0 else "۰ گرم",
            }
            
        except ImportError:
            # Gold installments module not available
            return {
                'has_installments': False,
                'contract_count': 0,
                'total_gold_debt_grams': 0.0,
                'current_toman_value': 0.0,
                'formatted_gold_debt': "۰ گرم",
            }
    
    @classmethod
    def _format_balance_display(cls, balance: Decimal) -> str:
        """
        Format balance for Persian display.
        
        Args:
            balance: Balance amount
            
        Returns:
            Formatted balance string in Persian
        """
        from zargar.core.persian_number_formatter import PersianNumberFormatter
        
        formatter = PersianNumberFormatter()
        
        if balance > 0:
            return f"بدهکار: {formatter.format_currency(balance, use_persian_digits=True)}"
        elif balance < 0:
            return f"بستانکار: {formatter.format_currency(abs(balance), use_persian_digits=True)}"
        else:
            return "تسویه"
    
    @classmethod
    def get_customer_transaction_history(cls, customer: Customer, limit: int = 10) -> List[Dict]:
        """
        Get customer's recent transaction history.
        
        Args:
            customer: Customer instance
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction dictionaries
        """
        transactions = POSTransaction.objects.filter(
            customer=customer
        ).select_related().order_by('-transaction_date')[:limit]
        
        transaction_data = []
        for transaction in transactions:
            formatted_data = transaction.format_for_display()
            transaction_data.append({
                'transaction_id': str(transaction.transaction_id),
                'transaction_number': transaction.transaction_number,
                'transaction_date': transaction.transaction_date.isoformat(),
                'transaction_date_shamsi': transaction.transaction_date_shamsi,
                'transaction_type': transaction.get_transaction_type_display(),
                'status': transaction.get_status_display(),
                'total_amount': float(transaction.total_amount),
                'amount_paid': float(transaction.amount_paid),
                'payment_method': transaction.get_payment_method_display(),
                'formatted_data': formatted_data,
                'has_invoice': hasattr(transaction, 'invoice'),
            })
        
        return transaction_data
    
    @classmethod
    def process_customer_payment(cls, customer: Customer, amount: Decimal,
                               payment_method: str = 'cash',
                               reference_number: str = '',
                               notes: str = '') -> Dict:
        """
        Process a payment from customer to reduce their debt balance.
        
        Args:
            customer: Customer instance
            amount: Payment amount
            payment_method: Payment method
            reference_number: Payment reference
            notes: Payment notes
            
        Returns:
            Dictionary with payment processing results
        """
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")
        
        # Get current balance
        balance_info = cls.get_customer_balance(customer)
        current_debt = Decimal(str(balance_info['current_balance']))
        
        if current_debt <= 0:
            raise ValidationError("Customer has no outstanding debt")
        
        # Create payment transaction
        payment_transaction = POSTransaction.objects.create(
            customer=customer,
            transaction_type='payment',
            payment_method=payment_method,
            amount_paid=amount,
            total_amount=amount,
            reference_number=reference_number,
            transaction_notes=notes,
            status='completed'
        )
        
        # Update customer stats
        customer.last_purchase_date = timezone.now()
        customer.save(update_fields=['last_purchase_date', 'updated_at'])
        
        # Calculate new balance
        new_balance = current_debt - amount
        
        logger.info(f"Processed payment of {amount} Toman for customer {customer}")
        
        return {
            'success': True,
            'payment_transaction': payment_transaction,
            'previous_balance': float(current_debt),
            'payment_amount': float(amount),
            'new_balance': float(new_balance),
            'balance_cleared': new_balance <= 0,
        }
    
    @classmethod
    def create_customer_credit(cls, customer: Customer, amount: Decimal,
                             reason: str = '',
                             reference_number: str = '') -> Dict:
        """
        Create a credit for customer (shop owes money to customer).
        
        Args:
            customer: Customer instance
            amount: Credit amount
            reason: Reason for credit
            reference_number: Reference number
            
        Returns:
            Dictionary with credit creation results
        """
        if amount <= 0:
            raise ValidationError("Credit amount must be positive")
        
        # Create credit transaction (negative amount)
        credit_transaction = POSTransaction.objects.create(
            customer=customer,
            transaction_type='credit',
            total_amount=-amount,  # Negative for credit
            amount_paid=0,
            transaction_notes=reason,
            reference_number=reference_number,
            status='completed'
        )
        
        logger.info(f"Created credit of {amount} Toman for customer {customer}")
        
        return {
            'success': True,
            'credit_transaction': credit_transaction,
            'credit_amount': float(amount),
            'reason': reason,
        }
    
    @classmethod
    def get_customer_detailed_info(cls, customer_id: int) -> Dict:
        """
        Get comprehensive customer information for POS display.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Dictionary with detailed customer information
        """
        try:
            customer = Customer.objects.get(id=customer_id, is_active=True)
        except Customer.DoesNotExist:
            raise ValidationError(f"Customer with ID {customer_id} not found")
        
        # Get balance information
        balance_info = cls.get_customer_balance(customer)
        
        # Get recent transactions
        recent_transactions = cls.get_customer_transaction_history(customer, limit=5)
        
        # Get loyalty information
        loyalty_info = {
            'current_points': customer.loyalty_points,
            'total_purchases': float(customer.total_purchases),
            'is_vip': customer.is_vip,
            'customer_type': customer.get_customer_type_display(),
        }
        
        # Get notes
        recent_notes = customer.notes.filter(is_resolved=False).order_by('-created_at')[:3]
        notes_data = []
        for note in recent_notes:
            notes_data.append({
                'title': note.title,
                'content': note.content,
                'note_type': note.get_note_type_display(),
                'is_important': note.is_important,
                'created_at': note.created_at.isoformat(),
            })
        
        return {
            'customer_info': {
                'id': customer.id,
                'name': str(customer),
                'full_persian_name': customer.full_persian_name,
                'phone_number': customer.phone_number,
                'email': customer.email or '',
                'address': customer.address or '',
                'birth_date_shamsi': customer.birth_date_shamsi or '',
                'national_id': customer.national_id or '',
                'is_birthday_today': customer.is_birthday_today,
            },
            'balance_info': balance_info,
            'loyalty_info': loyalty_info,
            'recent_transactions': recent_transactions,
            'recent_notes': notes_data,
            'last_purchase_date': customer.last_purchase_date.isoformat() if customer.last_purchase_date else None,
        }


class POSReportingService:
    """
    Service for POS reporting and analytics.
    """
    
    @classmethod
    def get_daily_sales_summary(cls, date: Optional[datetime] = None) -> Dict:
        """
        Get daily sales summary for POS transactions.
        
        Args:
            date: Specific date (defaults to today)
            
        Returns:
            Dictionary with daily sales summary
        """
        if date is None:
            date = timezone.now().date()
        
        # Get completed transactions for the date
        transactions = POSTransaction.objects.filter(
            transaction_date__date=date,
            status='completed'
        )
        
        # Calculate summary metrics
        total_transactions = transactions.count()
        total_sales = sum(t.total_amount for t in transactions)
        total_gold_weight = sum(t.total_gold_weight_grams for t in transactions)
        
        # Payment method breakdown
        payment_methods = {}
        for transaction in transactions:
            method = transaction.payment_method
            if method not in payment_methods:
                payment_methods[method] = {'count': 0, 'amount': Decimal('0.00')}
            payment_methods[method]['count'] += 1
            payment_methods[method]['amount'] += transaction.total_amount
        
        # Top selling items
        line_items = POSTransactionLineItem.objects.filter(
            transaction__in=transactions
        ).select_related('jewelry_item')
        
        item_sales = {}
        for line_item in line_items:
            item_key = line_item.item_sku or line_item.item_name
            if item_key not in item_sales:
                item_sales[item_key] = {
                    'name': line_item.item_name,
                    'quantity': 0,
                    'revenue': Decimal('0.00')
                }
            item_sales[item_key]['quantity'] += line_item.quantity
            item_sales[item_key]['revenue'] += line_item.line_total
        
        # Sort by revenue
        top_items = sorted(
            item_sales.values(),
            key=lambda x: x['revenue'],
            reverse=True
        )[:10]
        
        return {
            'date': date,
            'total_transactions': total_transactions,
            'total_sales': total_sales,
            'total_gold_weight': total_gold_weight,
            'average_transaction_value': total_sales / total_transactions if total_transactions > 0 else Decimal('0.00'),
            'payment_methods': payment_methods,
            'top_selling_items': top_items
        }
    
    @classmethod
    def get_monthly_sales_trend(cls, year: int, month: int) -> Dict:
        """
        Get monthly sales trend data.
        
        Args:
            year: Year
            month: Month
            
        Returns:
            Dictionary with monthly trend data
        """
        from calendar import monthrange
        
        # Get date range for the month
        start_date = datetime(year, month, 1).date()
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day).date()
        
        # Get transactions for the month
        transactions = POSTransaction.objects.filter(
            transaction_date__date__range=[start_date, end_date],
            status='completed'
        )
        
        # Group by day
        daily_data = {}
        for day in range(1, last_day + 1):
            daily_data[day] = {
                'date': datetime(year, month, day).date(),
                'transactions': 0,
                'sales': Decimal('0.00'),
                'gold_weight': Decimal('0.000')
            }
        
        for transaction in transactions:
            day = transaction.transaction_date.day
            daily_data[day]['transactions'] += 1
            daily_data[day]['sales'] += transaction.total_amount
            daily_data[day]['gold_weight'] += transaction.total_gold_weight_grams
        
        return {
            'year': year,
            'month': month,
            'daily_data': list(daily_data.values()),
            'total_transactions': transactions.count(),
            'total_sales': sum(t.total_amount for t in transactions),
            'total_gold_weight': sum(t.total_gold_weight_grams for t in transactions)
        }