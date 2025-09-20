"""
Billing services for subscription management and invoice generation.
Adapted for Iranian market and Persian business practices.
"""
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import jdatetime
from decimal import Decimal
import logging

from .admin_models import SubscriptionPlan, TenantInvoice, BillingCycle, TenantAccessLog
from .models import Tenant

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Manages subscription plans and tenant subscriptions.
    """
    
    @staticmethod
    def get_available_plans():
        """Get all active subscription plans."""
        return SubscriptionPlan.objects.filter(is_active=True).order_by('monthly_price_toman')
    
    @staticmethod
    def get_plan_by_type(plan_type):
        """Get subscription plan by type."""
        try:
            return SubscriptionPlan.objects.get(plan_type=plan_type, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return None
    
    @staticmethod
    def create_default_plans():
        """Create default subscription plans for Iranian market."""
        plans_data = [
            {
                'name': 'Basic Plan',
                'name_persian': 'پلن پایه',
                'plan_type': 'basic',
                'monthly_price_toman': Decimal('500000'),  # 500,000 Toman
                'yearly_price_toman': Decimal('5000000'),  # 5,000,000 Toman (2 months free)
                'max_users': 2,
                'max_inventory_items': 1000,
                'max_customers': 500,
                'max_monthly_transactions': 1000,
                'max_storage_gb': 5,
                'features': {
                    'pos_system': True,
                    'inventory_management': True,
                    'customer_management': True,
                    'accounting_system': False,
                    'gold_installment': False,
                    'reporting': True,
                    'backup_restore': True,
                    'multi_user': True,
                    'mobile_app': False,
                    'priority_support': False,
                    'custom_reports': False,
                    'api_access': False,
                }
            },
            {
                'name': 'Pro Plan',
                'name_persian': 'پلن حرفه‌ای',
                'plan_type': 'pro',
                'monthly_price_toman': Decimal('1200000'),  # 1,200,000 Toman
                'yearly_price_toman': Decimal('12000000'),  # 12,000,000 Toman (2 months free)
                'max_users': 5,
                'max_inventory_items': 5000,
                'max_customers': 2000,
                'max_monthly_transactions': 5000,
                'max_storage_gb': 20,
                'features': {
                    'pos_system': True,
                    'inventory_management': True,
                    'customer_management': True,
                    'accounting_system': True,
                    'gold_installment': True,
                    'reporting': True,
                    'backup_restore': True,
                    'multi_user': True,
                    'mobile_app': True,
                    'priority_support': True,
                    'custom_reports': True,
                    'api_access': False,
                },
                'is_popular': True
            },
            {
                'name': 'Enterprise Plan',
                'name_persian': 'پلن سازمانی',
                'plan_type': 'enterprise',
                'monthly_price_toman': Decimal('2500000'),  # 2,500,000 Toman
                'yearly_price_toman': Decimal('25000000'),  # 25,000,000 Toman (2 months free)
                'max_users': 20,
                'max_inventory_items': 50000,
                'max_customers': 10000,
                'max_monthly_transactions': 50000,
                'max_storage_gb': 100,
                'features': {
                    'pos_system': True,
                    'inventory_management': True,
                    'customer_management': True,
                    'accounting_system': True,
                    'gold_installment': True,
                    'reporting': True,
                    'backup_restore': True,
                    'multi_user': True,
                    'mobile_app': True,
                    'priority_support': True,
                    'custom_reports': True,
                    'api_access': True,
                }
            }
        ]
        
        created_plans = []
        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            if created:
                created_plans.append(plan)
                logger.info(f"Created subscription plan: {plan.name_persian}")
        
        return created_plans
    
    @staticmethod
    def upgrade_tenant_plan(tenant, new_plan, admin_user=None):
        """Upgrade tenant to a new subscription plan."""
        old_plan = tenant.subscription_plan_fk
        
        with transaction.atomic():
            tenant.subscription_plan_fk = new_plan
            tenant.save()
            
            # Log the upgrade
            TenantAccessLog.log_action(
                user=admin_user,
                tenant_schema=tenant.schema_name,
                action='update',
                model_name='Tenant',
                object_id=str(tenant.id),
                details={
                    'action': 'plan_upgrade',
                    'old_plan': old_plan.name_persian if old_plan else 'None',
                    'new_plan': new_plan.name_persian,
                    'old_price': str(old_plan.monthly_price_toman) if old_plan else '0',
                    'new_price': str(new_plan.monthly_price_toman)
                }
            )
            
            logger.info(f"Upgraded tenant {tenant.name} from {old_plan} to {new_plan}")
        
        return True
    
    @staticmethod
    def check_plan_limits(tenant):
        """Check if tenant is within their plan limits."""
        if not tenant.subscription_plan_fk:
            return {'within_limits': True, 'warnings': []}
        
        plan = tenant.subscription_plan_fk
        warnings = []
        
        # This would check actual usage against plan limits
        # For now, return placeholder structure
        usage_data = {
            'users_count': 0,  # Would query actual user count
            'inventory_items_count': 0,  # Would query actual inventory
            'customers_count': 0,  # Would query actual customers
            'monthly_transactions_count': 0,  # Would query current month transactions
            'storage_used_gb': 0,  # Would calculate actual storage usage
        }
        
        # Check limits
        if usage_data['users_count'] >= plan.max_users:
            warnings.append(_('User limit reached'))
        
        if usage_data['inventory_items_count'] >= plan.max_inventory_items:
            warnings.append(_('Inventory items limit reached'))
        
        if usage_data['customers_count'] >= plan.max_customers:
            warnings.append(_('Customer limit reached'))
        
        if usage_data['monthly_transactions_count'] >= plan.max_monthly_transactions:
            warnings.append(_('Monthly transaction limit reached'))
        
        if usage_data['storage_used_gb'] >= plan.max_storage_gb:
            warnings.append(_('Storage limit reached'))
        
        return {
            'within_limits': len(warnings) == 0,
            'warnings': warnings,
            'usage_data': usage_data,
            'plan_limits': {
                'max_users': plan.max_users,
                'max_inventory_items': plan.max_inventory_items,
                'max_customers': plan.max_customers,
                'max_monthly_transactions': plan.max_monthly_transactions,
                'max_storage_gb': plan.max_storage_gb,
            }
        }


class InvoiceGenerator:
    """
    Generates invoices for tenant billing with Persian formatting.
    """
    
    @staticmethod
    def generate_monthly_invoice(tenant, billing_month=None, admin_user=None):
        """Generate monthly invoice for a tenant."""
        subscription_plan = tenant.subscription_plan_fk
        if not subscription_plan:
            raise ValueError(f"Tenant {tenant.name} has no subscription plan")
        
        if billing_month is None:
            billing_month = jdatetime.date.today().replace(day=1)
        
        # Calculate billing period
        billing_period_start = billing_month
        if billing_month.month == 12:
            billing_period_end = billing_month.replace(year=billing_month.year + 1, month=1, day=1) - jdatetime.timedelta(days=1)
        else:
            billing_period_end = billing_month.replace(month=billing_month.month + 1, day=1) - jdatetime.timedelta(days=1)
        
        # Check if invoice already exists for this period
        existing_invoice = TenantInvoice.objects.filter(
            tenant=tenant,
            billing_period_start=billing_period_start.togregorian(),
            billing_period_end=billing_period_end.togregorian()
        ).first()
        
        if existing_invoice:
            logger.warning(f"Invoice already exists for tenant {tenant.name} for period {billing_period_start}")
            return existing_invoice
        
        # Create invoice
        with transaction.atomic():
            invoice = TenantInvoice.objects.create(
                tenant=tenant,
                subscription_plan=subscription_plan,
                issue_date_shamsi=jdatetime.date.today().togregorian(),
                due_date_shamsi=(jdatetime.date.today() + jdatetime.timedelta(days=30)).togregorian(),
                billing_period_start=billing_period_start.togregorian(),
                billing_period_end=billing_period_end.togregorian(),
                subtotal_toman=subscription_plan.monthly_price_toman,
                created_by=admin_user,
                line_items=[
                    {
                        'description': f'اشتراک ماهانه - {subscription_plan.name_persian}',
                        'description_english': f'Monthly Subscription - {subscription_plan.name}',
                        'quantity': 1,
                        'unit_price': str(subscription_plan.monthly_price_toman),
                        'total_price': str(subscription_plan.monthly_price_toman),
                        'period_start': billing_period_start.strftime('%Y/%m/%d'),
                        'period_end': billing_period_end.strftime('%Y/%m/%d')
                    }
                ],
                notes=f'فاکتور اشتراک ماهانه برای دوره {billing_period_start.strftime("%Y/%m/%d")} تا {billing_period_end.strftime("%Y/%m/%d")}'
            )
            
            # Log invoice creation
            TenantAccessLog.log_action(
                user=admin_user,
                tenant_schema=tenant.schema_name,
                action='create',
                model_name='TenantInvoice',
                object_id=str(invoice.id),
                details={
                    'action': 'invoice_generated',
                    'invoice_number': invoice.invoice_number,
                    'amount': str(invoice.total_amount_toman),
                    'billing_period': f"{billing_period_start} to {billing_period_end}"
                }
            )
            
            logger.info(f"Generated invoice {invoice.invoice_number} for tenant {tenant.name}")
        
        return invoice
    
    @staticmethod
    def generate_yearly_invoice(tenant, billing_year=None, admin_user=None):
        """Generate yearly invoice for a tenant."""
        subscription_plan = tenant.subscription_plan_fk
        if not subscription_plan or not subscription_plan.yearly_price_toman:
            raise ValueError(f"Tenant {tenant.name} has no yearly pricing available")
        
        if billing_year is None:
            billing_year = jdatetime.date.today().year
        
        # Calculate billing period (full year)
        billing_period_start = jdatetime.date(billing_year, 1, 1)
        billing_period_end = jdatetime.date(billing_year, 12, 29)  # Persian calendar last day
        
        # Check if invoice already exists for this year
        existing_invoice = TenantInvoice.objects.filter(
            tenant=tenant,
            billing_period_start=billing_period_start.togregorian(),
            billing_period_end=billing_period_end.togregorian()
        ).first()
        
        if existing_invoice:
            logger.warning(f"Yearly invoice already exists for tenant {tenant.name} for year {billing_year}")
            return existing_invoice
        
        # Calculate discount
        monthly_total = subscription_plan.monthly_price_toman * 12
        yearly_price = subscription_plan.yearly_price_toman
        discount_amount = monthly_total - yearly_price
        
        # Create invoice
        with transaction.atomic():
            invoice = TenantInvoice.objects.create(
                tenant=tenant,
                subscription_plan=subscription_plan,
                issue_date_shamsi=jdatetime.date.today().togregorian(),
                due_date_shamsi=(jdatetime.date.today() + jdatetime.timedelta(days=30)).togregorian(),
                billing_period_start=billing_period_start.togregorian(),
                billing_period_end=billing_period_end.togregorian(),
                subtotal_toman=monthly_total,
                discount_amount_toman=discount_amount,
                created_by=admin_user,
                line_items=[
                    {
                        'description': f'اشتراک سالانه - {subscription_plan.name_persian}',
                        'description_english': f'Yearly Subscription - {subscription_plan.name}',
                        'quantity': 12,
                        'unit_price': str(subscription_plan.monthly_price_toman),
                        'total_price': str(monthly_total),
                        'period_start': billing_period_start.strftime('%Y/%m/%d'),
                        'period_end': billing_period_end.strftime('%Y/%m/%d')
                    },
                    {
                        'description': f'تخفیف اشتراک سالانه ({subscription_plan.yearly_discount_percentage}%)',
                        'description_english': f'Yearly Subscription Discount ({subscription_plan.yearly_discount_percentage}%)',
                        'quantity': 1,
                        'unit_price': str(-discount_amount),
                        'total_price': str(-discount_amount),
                        'is_discount': True
                    }
                ],
                notes=f'فاکتور اشتراک سالانه برای سال {billing_year} با تخفیف {subscription_plan.yearly_discount_percentage}%'
            )
            
            # Log invoice creation
            TenantAccessLog.log_action(
                user=admin_user,
                tenant_schema=tenant.schema_name,
                action='create',
                model_name='TenantInvoice',
                object_id=str(invoice.id),
                details={
                    'action': 'yearly_invoice_generated',
                    'invoice_number': invoice.invoice_number,
                    'amount': str(invoice.total_amount_toman),
                    'discount_amount': str(discount_amount),
                    'billing_year': billing_year
                }
            )
            
            logger.info(f"Generated yearly invoice {invoice.invoice_number} for tenant {tenant.name}")
        
        return invoice
    
    @staticmethod
    def send_invoice_notification(invoice, notification_type='email'):
        """Send invoice notification to tenant."""
        tenant = invoice.tenant
        
        if notification_type == 'email' and tenant.owner_email:
            subject = f'فاکتور جدید - {invoice.invoice_number}'
            
            context = {
                'invoice': invoice,
                'tenant': tenant,
                'persian_date': jdatetime.date.today().strftime('%Y/%m/%d')
            }
            
            html_message = render_to_string('admin/billing/invoice_email.html', context)
            plain_message = render_to_string('admin/billing/invoice_email.txt', context)
            
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.owner_email],
                    html_message=html_message,
                    fail_silently=False
                )
                
                logger.info(f"Sent invoice email for {invoice.invoice_number} to {tenant.owner_email}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to send invoice email for {invoice.invoice_number}: {str(e)}")
                return False
        
        # SMS notification would be implemented here for Iranian SMS services
        elif notification_type == 'sms' and tenant.phone_number:
            # Placeholder for SMS integration
            logger.info(f"SMS notification for invoice {invoice.invoice_number} would be sent to {tenant.phone_number}")
            return True
        
        return False


class BillingWorkflow:
    """
    Manages the complete billing workflow for Iranian market.
    """
    
    @staticmethod
    def setup_tenant_billing(tenant, cycle_type='monthly', billing_day=1, admin_user=None):
        """Setup billing cycle for a new tenant."""
        
        # Calculate next billing date
        current_date = jdatetime.date.today()
        if cycle_type == 'monthly':
            next_billing = current_date.replace(day=billing_day)
            if next_billing <= current_date:
                # Next month
                if current_date.month == 12:
                    next_billing = next_billing.replace(year=current_date.year + 1, month=1)
                else:
                    next_billing = next_billing.replace(month=current_date.month + 1)
        else:
            next_billing = current_date + jdatetime.timedelta(days=30)
        
        # Create or update billing cycle
        billing_cycle, created = BillingCycle.objects.get_or_create(
            tenant=tenant,
            defaults={
                'cycle_type': cycle_type,
                'next_billing_date': next_billing.togregorian(),
                'billing_day': billing_day,
                'is_active': True
            }
        )
        
        if not created:
            billing_cycle.cycle_type = cycle_type
            billing_cycle.next_billing_date = next_billing.togregorian()
            billing_cycle.billing_day = billing_day
            billing_cycle.is_active = True
            billing_cycle.save()
        
        # Log billing setup
        TenantAccessLog.log_action(
            user=admin_user,
            tenant_schema=tenant.schema_name,
            action='create' if created else 'update',
            model_name='BillingCycle',
            object_id=str(billing_cycle.id),
            details={
                'action': 'billing_setup',
                'cycle_type': cycle_type,
                'next_billing_date': next_billing.strftime('%Y/%m/%d'),
                'billing_day': billing_day
            }
        )
        
        logger.info(f"Setup billing cycle for tenant {tenant.name}: {cycle_type}, next billing: {next_billing}")
        
        return billing_cycle
    
    @staticmethod
    def process_due_invoices():
        """Process all due invoices and send reminders."""
        current_date = jdatetime.date.today()
        
        # Get overdue invoices (compare with Gregorian date)
        overdue_invoices = TenantInvoice.objects.filter(
            status='pending',
            due_date_shamsi__lt=current_date.togregorian()
        )
        
        for invoice in overdue_invoices:
            # Mark as overdue
            invoice.status = 'overdue'
            invoice.save()
            
            # Send reminder
            InvoiceGenerator.send_invoice_notification(invoice, 'email')
            
            # Check if tenant should be suspended
            days_overdue = invoice.days_overdue
            grace_period = getattr(invoice.tenant.billing_cycle, 'grace_period_days', 7)
            
            if days_overdue > grace_period:
                # Suspend tenant
                invoice.tenant.is_active = False
                invoice.tenant.save()
                
                logger.warning(f"Suspended tenant {invoice.tenant.name} due to overdue invoice {invoice.invoice_number}")
        
        return len(overdue_invoices)
    
    @staticmethod
    def generate_monthly_invoices_batch(admin_user=None):
        """Generate monthly invoices for all active tenants."""
        current_date = jdatetime.date.today()
        
        # Get tenants with billing due today (compare with Gregorian date)
        billing_cycles = BillingCycle.objects.filter(
            is_active=True,
            cycle_type='monthly',
            next_billing_date__lte=current_date.togregorian(),
            tenant__is_active=True
        )
        
        generated_invoices = []
        
        for billing_cycle in billing_cycles:
            try:
                # Generate invoice
                invoice = InvoiceGenerator.generate_monthly_invoice(
                    tenant=billing_cycle.tenant,
                    admin_user=admin_user
                )
                
                # Send notification
                InvoiceGenerator.send_invoice_notification(invoice)
                
                # Update next billing date
                billing_cycle.calculate_next_billing_date()
                
                generated_invoices.append(invoice)
                
            except Exception as e:
                logger.error(f"Failed to generate invoice for tenant {billing_cycle.tenant.name}: {str(e)}")
        
        logger.info(f"Generated {len(generated_invoices)} monthly invoices")
        
        return generated_invoices
    
    @staticmethod
    def manual_payment_processing(invoice, payment_method, payment_reference='', admin_user=None):
        """Process manual payment for Iranian market."""
        if invoice.status == 'paid':
            raise ValueError(f"Invoice {invoice.invoice_number} is already paid")
        
        with transaction.atomic():
            # Mark invoice as paid
            invoice.mark_as_paid(
                payment_method=payment_method,
                payment_reference=payment_reference
            )
            
            # Reactivate tenant if suspended
            if not invoice.tenant.is_active:
                invoice.tenant.is_active = True
                invoice.tenant.save()
                
                logger.info(f"Reactivated tenant {invoice.tenant.name} after payment")
            
            # Log payment processing
            TenantAccessLog.log_action(
                user=admin_user,
                tenant_schema=invoice.tenant.schema_name,
                action='update',
                model_name='TenantInvoice',
                object_id=str(invoice.id),
                details={
                    'action': 'manual_payment_processed',
                    'invoice_number': invoice.invoice_number,
                    'amount': str(invoice.total_amount_toman),
                    'payment_method': payment_method,
                    'payment_reference': payment_reference,
                    'processed_by': admin_user.username if admin_user else 'system'
                }
            )
        
        logger.info(f"Processed manual payment for invoice {invoice.invoice_number}")
        
        return True