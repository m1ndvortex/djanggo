"""
Celery tasks for gold installment system.
Handles background processing for gold price updates and payment processing.
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
import logging
from typing import Dict, List

from .services import GoldPriceService, PaymentProcessingService
from .models import GoldInstallmentContract, GoldInstallmentPayment

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def update_gold_prices(self, karats: List[int] = None):
    """
    Update gold prices from Iranian market APIs.
    
    Args:
        karats: List of karats to update (defaults to [14, 18, 21, 22, 24])
    """
    if karats is None:
        karats = [14, 18, 21, 22, 24]
    
    try:
        updated_prices = {}
        
        for karat in karats:
            # Invalidate cache to force fresh fetch
            GoldPriceService.invalidate_cache(karat)
            
            # Fetch new price
            price_data = GoldPriceService.get_current_gold_price(karat)
            updated_prices[karat] = price_data
            
            logger.info(f"Updated gold price for {karat}k: {price_data['price_per_gram']} "
                       f"from {price_data['source']}")
        
        return {
            'success': True,
            'updated_prices': updated_prices,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error updating gold prices: {exc}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        
        return {
            'success': False,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def process_scheduled_payment(self, contract_id: int, payment_amount: Decimal, 
                             payment_method: str = 'auto'):
    """
    Process a scheduled payment for a gold installment contract.
    
    Args:
        contract_id: GoldInstallmentContract ID
        payment_amount: Payment amount in Toman
        payment_method: Payment method
    """
    try:
        contract = GoldInstallmentContract.objects.get(id=contract_id)
        
        if contract.status != 'active':
            logger.warning(f"Skipping scheduled payment for inactive contract {contract.contract_number}")
            return {
                'success': False,
                'error': f'Contract status is {contract.status}',
                'contract_id': contract_id
            }
        
        # Process the payment
        result = PaymentProcessingService.process_payment(
            contract=contract,
            payment_amount=payment_amount,
            payment_method=payment_method,
            notes='Scheduled automatic payment'
        )
        
        logger.info(f"Processed scheduled payment for contract {contract.contract_number}: "
                   f"{payment_amount} Toman")
        
        return {
            'success': True,
            'contract_id': contract_id,
            'payment_id': result['payment'].id,
            'remaining_balance': result['remaining_balance']
        }
        
    except GoldInstallmentContract.DoesNotExist:
        logger.error(f"Contract with ID {contract_id} not found")
        return {
            'success': False,
            'error': 'Contract not found',
            'contract_id': contract_id
        }
    except Exception as exc:
        logger.error(f"Error processing scheduled payment for contract {contract_id}: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'contract_id': contract_id
        }


@shared_task
def send_payment_reminders():
    """
    Send payment reminders for overdue gold installment contracts.
    """
    try:
        # Find overdue contracts
        overdue_contracts = []
        active_contracts = GoldInstallmentContract.objects.filter(status='active')
        
        for contract in active_contracts:
            if contract.is_overdue:
                overdue_contracts.append(contract)
        
        reminder_count = 0
        
        for contract in overdue_contracts:
            try:
                # Send reminder (email/SMS)
                send_contract_payment_reminder(contract)
                reminder_count += 1
                
                logger.info(f"Sent payment reminder for contract {contract.contract_number}")
                
            except Exception as e:
                logger.error(f"Failed to send reminder for contract {contract.contract_number}: {e}")
                continue
        
        return {
            'success': True,
            'overdue_contracts_found': len(overdue_contracts),
            'reminders_sent': reminder_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error sending payment reminders: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def calculate_daily_contract_metrics():
    """
    Calculate daily metrics for all active gold installment contracts.
    """
    try:
        active_contracts = GoldInstallmentContract.objects.filter(status='active')
        
        metrics = {
            'total_active_contracts': active_contracts.count(),
            'total_remaining_gold_weight': Decimal('0.000'),
            'total_remaining_value': Decimal('0.00'),
            'overdue_contracts': 0,
            'contracts_near_completion': 0,
            'price_protection_active': 0
        }
        
        # Get current gold prices for calculations
        gold_prices = {}
        for karat in [14, 18, 21, 22, 24]:
            price_data = GoldPriceService.get_current_gold_price(karat)
            gold_prices[karat] = price_data['price_per_gram']
        
        for contract in active_contracts:
            # Add to total remaining weight
            metrics['total_remaining_gold_weight'] += contract.remaining_gold_weight_grams
            
            # Calculate remaining value
            gold_price = gold_prices.get(contract.gold_karat, gold_prices[18])
            remaining_value = contract.remaining_gold_weight_grams * gold_price
            metrics['total_remaining_value'] += remaining_value
            
            # Check if overdue
            if contract.is_overdue:
                metrics['overdue_contracts'] += 1
            
            # Check if near completion (>90%)
            if contract.completion_percentage >= 90:
                metrics['contracts_near_completion'] += 1
            
            # Check price protection
            if contract.has_price_protection:
                metrics['price_protection_active'] += 1
        
        # Convert Decimal to string for JSON serialization
        for key, value in metrics.items():
            if isinstance(value, Decimal):
                metrics[key] = str(value)
        
        logger.info(f"Calculated daily contract metrics: {metrics}")
        
        return {
            'success': True,
            'metrics': metrics,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error calculating daily contract metrics: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def analyze_price_protection_impact():
    """
    Analyze the impact of price protection across all contracts.
    """
    try:
        protected_contracts = GoldInstallmentContract.objects.filter(
            has_price_protection=True,
            status='active'
        )
        
        analysis_results = {
            'total_protected_contracts': protected_contracts.count(),
            'ceiling_protection_active': 0,
            'floor_protection_active': 0,
            'total_customer_savings': Decimal('0.00'),
            'total_shop_cost': Decimal('0.00'),
            'contracts_analyzed': []
        }
        
        for contract in protected_contracts:
            from .services import GoldPriceProtectionService
            
            impact = GoldPriceProtectionService.analyze_price_protection_impact(contract)
            
            if impact['protection_active']:
                if impact['protection_type'] == 'ceiling':
                    analysis_results['ceiling_protection_active'] += 1
                elif impact['protection_type'] == 'floor':
                    analysis_results['floor_protection_active'] += 1
                
                # Track financial impact
                if impact['customer_benefit']:
                    analysis_results['total_customer_savings'] += abs(impact['value_impact'])
                else:
                    analysis_results['total_shop_cost'] += abs(impact['value_impact'])
                
                analysis_results['contracts_analyzed'].append({
                    'contract_number': contract.contract_number,
                    'protection_type': impact['protection_type'],
                    'value_impact': str(impact['value_impact']),
                    'customer_benefit': impact['customer_benefit']
                })
        
        # Convert Decimal to string for JSON serialization
        analysis_results['total_customer_savings'] = str(analysis_results['total_customer_savings'])
        analysis_results['total_shop_cost'] = str(analysis_results['total_shop_cost'])
        
        logger.info(f"Analyzed price protection impact: {len(analysis_results['contracts_analyzed'])} contracts")
        
        return {
            'success': True,
            'analysis': analysis_results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error analyzing price protection impact: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


def send_contract_payment_reminder(contract: GoldInstallmentContract):
    """
    Send payment reminder for a specific contract.
    
    Args:
        contract: GoldInstallmentContract instance
    """
    # Get customer contact information
    customer = contract.customer
    
    # Calculate overdue amount
    gold_price_data = GoldPriceService.get_current_gold_price(contract.gold_karat)
    remaining_value = contract.remaining_gold_weight_grams * gold_price_data['price_per_gram']
    
    # Prepare reminder message
    message = f"""
    سلام {customer.persian_first_name} {customer.persian_last_name} عزیز،
    
    یادآوری پرداخت قرارداد طلای قرضی شماره {contract.contract_number}
    
    مانده طلا: {contract.remaining_gold_weight_grams} گرم
    ارزش تقریبی: {remaining_value:,.0f} تومان
    
    لطفاً در اسرع وقت برای پرداخت اقدام فرمایید.
    
    با تشکر،
    طلافروشی زرگر
    """
    
    # Send email if available
    if customer.email:
        try:
            send_mail(
                subject=f'یادآوری پرداخت قرارداد {contract.contract_number}',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer.email],
                fail_silently=False
            )
            logger.info(f"Sent email reminder to {customer.email} for contract {contract.contract_number}")
        except Exception as e:
            logger.error(f"Failed to send email reminder: {e}")
    
    # TODO: Implement SMS sending when SMS service is integrated
    # if customer.phone_number:
    #     send_sms(customer.phone_number, message)
    
    return True


@shared_task
def cleanup_expired_price_cache():
    """
    Clean up expired gold price cache entries.
    """
    try:
        # Invalidate all cached prices to force refresh
        GoldPriceService.invalidate_cache()
        
        logger.info("Cleaned up expired gold price cache entries")
        
        return {
            'success': True,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up price cache: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }