"""
Layaway and installment plan services for zargar project.
"""
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta, date
import jdatetime
from typing import Dict, List, Optional, Tuple

from .layaway_models import (
    LayawayPlan, LayawayScheduledPayment, LayawayPayment, 
    LayawayRefund, LayawayContract, LayawayReminder
)
from .models import Customer
from zargar.jewelry.models import JewelryItem


class LayawayPlanService:
    """
    Service class for managing layaway plans and installment payments.
    """
    
    @staticmethod
    def create_layaway_plan(
        customer: Customer,
        jewelry_item: JewelryItem,
        total_amount: Decimal,
        down_payment: Decimal,
        payment_frequency: str,
        number_of_payments: int,
        start_date: date = None,
        contract_template: LayawayContract = None,
        notes: str = ''
    ) -> LayawayPlan:
        """
        Create a new layaway plan with payment schedule.
        
        Args:
            customer: Customer for the layaway plan
            jewelry_item: Jewelry item to be purchased
            total_amount: Total purchase amount
            down_payment: Initial down payment
            payment_frequency: Payment frequency (weekly, bi_weekly, monthly)
            number_of_payments: Number of installment payments
            start_date: Plan start date (defaults to today)
            contract_template: Contract template to use
            notes: Additional notes
            
        Returns:
            Created LayawayPlan instance
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate inputs
        LayawayPlanService._validate_plan_inputs(
            customer, jewelry_item, total_amount, down_payment, number_of_payments
        )
        
        if start_date is None:
            start_date = timezone.now().date()
        
        # Calculate installment amount
        remaining_amount = total_amount - down_payment
        installment_amount = remaining_amount / number_of_payments
        
        # Get default contract if none provided
        if contract_template is None:
            contract_template = LayawayContract.objects.filter(
                is_default=True, is_active=True
            ).first()
        
        # Create layaway plan
        with transaction.atomic():
            plan = LayawayPlan.objects.create(
                customer=customer,
                jewelry_item=jewelry_item,
                total_amount=total_amount,
                down_payment=down_payment,
                installment_amount=installment_amount,
                payment_frequency=payment_frequency,
                number_of_payments=number_of_payments,
                start_date=start_date,
                expected_completion_date=LayawayPlanService._calculate_completion_date(
                    start_date, payment_frequency, number_of_payments
                ),
                contract_terms=contract_template.contract_template if contract_template else '',
                grace_period_days=contract_template.default_grace_period if contract_template else 7,
                notes=notes,
                total_paid=down_payment if down_payment > 0 else Decimal('0.00')
            )
            
            # Generate payment schedule
            plan.generate_payment_schedule()
            
            # Process down payment if provided
            if down_payment > 0:
                LayawayPlanService.process_payment(
                    plan, down_payment, 'cash', 'Down payment'
                )
            
            # Create initial reminder schedule
            LayawayReminderService.create_reminder_schedule(plan)
            
        return plan
    
    @staticmethod
    def _validate_plan_inputs(
        customer: Customer,
        jewelry_item: JewelryItem,
        total_amount: Decimal,
        down_payment: Decimal,
        number_of_payments: int
    ):
        """Validate layaway plan inputs."""
        if not customer.is_active:
            raise ValidationError("Customer account is not active")
        
        if jewelry_item.status not in ['in_stock', 'reserved']:
            raise ValidationError("Jewelry item is not available for layaway")
        
        if total_amount <= 0:
            raise ValidationError("Total amount must be positive")
        
        if down_payment < 0:
            raise ValidationError("Down payment cannot be negative")
        
        if down_payment >= total_amount:
            raise ValidationError("Down payment cannot be greater than or equal to total amount")
        
        if number_of_payments < 1 or number_of_payments > 120:
            raise ValidationError("Number of payments must be between 1 and 120")
        
        # Check if item has minimum selling price
        if jewelry_item.selling_price and total_amount < jewelry_item.selling_price:
            raise ValidationError(
                f"Total amount cannot be less than item selling price: {jewelry_item.selling_price}"
            )
    
    @staticmethod
    def _calculate_completion_date(start_date: date, frequency: str, num_payments: int) -> date:
        """Calculate expected completion date."""
        if frequency == 'weekly':
            days = 7 * num_payments
        elif frequency == 'bi_weekly':
            days = 14 * num_payments
        elif frequency == 'monthly':
            days = 30 * num_payments
        else:
            days = 30 * num_payments  # Default to monthly
        
        return start_date + timedelta(days=days)
    
    @staticmethod
    def process_payment(
        plan: LayawayPlan,
        amount: Decimal,
        payment_method: str = 'cash',
        notes: str = '',
        reference_number: str = ''
    ) -> LayawayPayment:
        """
        Process a payment for a layaway plan.
        
        Args:
            plan: LayawayPlan to process payment for
            amount: Payment amount
            payment_method: Payment method
            notes: Payment notes
            reference_number: Reference number for the payment
            
        Returns:
            Created LayawayPayment instance
            
        Raises:
            ValidationError: If payment processing fails
        """
        if plan.status != 'active':
            raise ValidationError("Cannot process payment for inactive plan")
        
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")
        
        with transaction.atomic():
            # Create payment record
            payment = LayawayPayment.objects.create(
                layaway_plan=plan,
                amount=amount,
                payment_method=payment_method,
                payment_date=timezone.now().date(),
                reference_number=reference_number,
                notes=notes
            )
            
            # Process the payment through the plan
            plan.process_payment(amount, payment_method, notes)
            
        return payment
    
    @staticmethod
    def cancel_plan(
        plan: LayawayPlan,
        reason: str,
        refund_percentage: Decimal = Decimal('90.00'),
        processed_by = None
    ) -> Optional[LayawayRefund]:
        """
        Cancel a layaway plan and process refund.
        
        Args:
            plan: LayawayPlan to cancel
            reason: Cancellation reason
            refund_percentage: Percentage of payments to refund
            processed_by: User processing the cancellation
            
        Returns:
            LayawayRefund instance if refund is issued, None otherwise
        """
        if plan.status in ['completed', 'cancelled']:
            raise ValidationError("Cannot cancel completed or already cancelled plan")
        
        with transaction.atomic():
            # Calculate refund amount
            refund_amount = (plan.total_paid * refund_percentage) / Decimal('100.00')
            
            # Cancel the plan
            plan.cancel_plan(reason, refund_amount)
            
            # Create refund record if amount > 0
            refund = None
            if refund_amount > 0:
                refund = LayawayRefund.objects.create(
                    layaway_plan=plan,
                    refund_amount=refund_amount,
                    reason=reason,
                    processed_by=processed_by
                )
            
        return refund
    
    @staticmethod
    def modify_payment_schedule(
        plan: LayawayPlan,
        new_frequency: str = None,
        new_installment_amount: Decimal = None,
        reason: str = ''
    ) -> bool:
        """
        Modify payment schedule for an active layaway plan.
        
        Args:
            plan: LayawayPlan to modify
            new_frequency: New payment frequency
            new_installment_amount: New installment amount
            reason: Reason for modification
            
        Returns:
            True if modification successful, False otherwise
        """
        if plan.status != 'active':
            raise ValidationError("Cannot modify inactive plan")
        
        with transaction.atomic():
            # Update plan details
            if new_frequency:
                plan.payment_frequency = new_frequency
            
            if new_installment_amount:
                plan.installment_amount = new_installment_amount
                # Recalculate number of payments
                remaining_balance = plan.remaining_balance
                plan.number_of_payments = int(remaining_balance / new_installment_amount) + 1
            
            # Add modification note
            plan.internal_notes += f"\nSchedule modified: {reason} - {timezone.now()}"
            
            # Regenerate payment schedule for remaining payments
            plan.scheduled_payments.filter(is_paid=False).delete()
            
            # Calculate new schedule starting from next unpaid payment
            current_date = timezone.now().date()
            if plan.payment_frequency == 'weekly':
                days_between = 7
            elif plan.payment_frequency == 'bi_weekly':
                days_between = 14
            else:
                days_between = 30
            
            # Create new scheduled payments
            remaining_payments = plan.number_of_payments - plan.payments_made
            for i in range(remaining_payments):
                payment_date = current_date + timedelta(days=days_between * (i + 1))
                
                LayawayScheduledPayment.objects.create(
                    layaway_plan=plan,
                    payment_number=plan.payments_made + i + 1,
                    due_date=payment_date,
                    amount=plan.installment_amount
                )
            
            plan.save()
        
        return True
    
    @staticmethod
    def get_overdue_plans(days_overdue: int = 0) -> List[LayawayPlan]:
        """
        Get layaway plans with overdue payments.
        
        Args:
            days_overdue: Minimum days overdue (0 for any overdue)
            
        Returns:
            List of overdue LayawayPlan instances
        """
        today = timezone.now().date()
        
        # Get plans with overdue scheduled payments
        overdue_plans = LayawayPlan.objects.filter(
            status='active',
            scheduled_payments__due_date__lt=today,
            scheduled_payments__is_paid=False
        ).distinct()
        
        if days_overdue > 0:
            # Filter by specific days overdue
            filtered_plans = []
            for plan in overdue_plans:
                if plan.days_overdue >= days_overdue:
                    filtered_plans.append(plan)
            return filtered_plans
        
        return list(overdue_plans)
    
    @staticmethod
    def get_upcoming_payments(days_ahead: int = 7) -> List[LayawayScheduledPayment]:
        """
        Get upcoming scheduled payments.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of upcoming LayawayScheduledPayment instances
        """
        today = timezone.now().date()
        future_date = today + timedelta(days=days_ahead)
        
        return LayawayScheduledPayment.objects.filter(
            due_date__gte=today,
            due_date__lte=future_date,
            is_paid=False,
            layaway_plan__status='active'
        ).order_by('due_date')
    
    @staticmethod
    def calculate_plan_statistics(plan: LayawayPlan) -> Dict:
        """
        Calculate comprehensive statistics for a layaway plan.
        
        Args:
            plan: LayawayPlan to analyze
            
        Returns:
            Dictionary with plan statistics
        """
        stats = {
            'completion_percentage': plan.completion_percentage,
            'total_paid': plan.total_paid,
            'remaining_balance': plan.remaining_balance,
            'payments_made': plan.payments_made,
            'payments_remaining': plan.number_of_payments - plan.payments_made,
            'is_overdue': plan.is_overdue,
            'days_overdue': plan.days_overdue,
            'next_payment_due': plan.next_payment_due,
            'next_payment_amount': plan.next_payment_amount,
            'expected_completion': plan.expected_completion_date,
        }
        
        # Calculate payment history
        payments = plan.payments.all()
        stats['payment_history'] = [
            {
                'date': payment.payment_date,
                'amount': payment.amount,
                'method': payment.get_payment_method_display(),
                'reference': payment.reference_number
            }
            for payment in payments
        ]
        
        # Calculate overdue fees if applicable
        if plan.is_overdue:
            overdue_payments = plan.scheduled_payments.filter(
                is_overdue=True,
                is_paid=False
            )
            stats['overdue_fees'] = sum(p.late_fee_applied for p in overdue_payments)
        else:
            stats['overdue_fees'] = Decimal('0.00')
        
        return stats


class LayawayReminderService:
    """
    Service class for managing layaway payment reminders.
    """
    
    @staticmethod
    def create_reminder_schedule(plan: LayawayPlan):
        """
        Create reminder schedule for a layaway plan.
        
        Args:
            plan: LayawayPlan to create reminders for
        """
        # Clear existing reminders
        plan.reminders.all().delete()
        
        # Create reminders for each scheduled payment
        for scheduled_payment in plan.scheduled_payments.all():
            # Upcoming payment reminder (3 days before)
            reminder_date = scheduled_payment.due_date - timedelta(days=3)
            if reminder_date >= timezone.now().date():
                LayawayReminder.objects.create(
                    layaway_plan=plan,
                    reminder_type='upcoming',
                    scheduled_date=reminder_date,
                    delivery_method='sms',
                    recipient=plan.customer.phone_number,
                    message_template=LayawayReminderService._get_upcoming_payment_template()
                )
    
    @staticmethod
    def _get_upcoming_payment_template() -> str:
        """Get template for upcoming payment reminder."""
        return """
سلام {{customer_name}} عزیز،

یادآوری پرداخت قسط طلای قرضی:
شماره قرارداد: {{plan_number}}
مبلغ قسط: {{next_payment_amount}} تومان
تاریخ سررسید: {{next_payment_date}}

برای پرداخت به فروشگاه مراجعه فرمایید.

با تشکر
        """.strip()
    
    @staticmethod
    def _get_overdue_payment_template() -> str:
        """Get template for overdue payment reminder."""
        return """
سلام {{customer_name}} عزیز،

قسط طلای قرضی شما معوق شده است:
شماره قرارداد: {{plan_number}}
مبلغ معوق: {{next_payment_amount}} تومان
تعداد روز تاخیر: {{days_overdue}} روز

لطفاً در اسرع وقت برای پرداخت اقدام فرمایید.

با تشکر
        """.strip()
    
    @staticmethod
    def send_overdue_reminders():
        """
        Send reminders for overdue payments.
        
        Returns:
            Number of reminders sent
        """
        overdue_plans = LayawayPlanService.get_overdue_plans(days_overdue=1)
        reminders_sent = 0
        
        for plan in overdue_plans:
            # Check if overdue reminder already sent today
            today = timezone.now().date()
            existing_reminder = plan.reminders.filter(
                reminder_type='overdue',
                scheduled_date=today,
                is_sent=True
            ).exists()
            
            if not existing_reminder:
                # Create and send overdue reminder
                reminder = LayawayReminder.objects.create(
                    layaway_plan=plan,
                    reminder_type='overdue',
                    scheduled_date=today,
                    delivery_method='sms',
                    recipient=plan.customer.phone_number,
                    message_template=LayawayReminderService._get_overdue_payment_template()
                )
                
                if reminder.send_reminder():
                    reminders_sent += 1
        
        return reminders_sent
    
    @staticmethod
    def send_upcoming_reminders():
        """
        Send reminders for upcoming payments.
        
        Returns:
            Number of reminders sent
        """
        today = timezone.now().date()
        
        # Get reminders scheduled for today
        pending_reminders = LayawayReminder.objects.filter(
            scheduled_date=today,
            is_sent=False,
            reminder_type='upcoming'
        )
        
        reminders_sent = 0
        for reminder in pending_reminders:
            if reminder.send_reminder():
                reminders_sent += 1
        
        return reminders_sent


class LayawayContractService:
    """
    Service class for managing layaway contracts.
    """
    
    @staticmethod
    def generate_contract_pdf(plan: LayawayPlan, contract_template: LayawayContract = None):
        """
        Generate PDF contract for a layaway plan.
        
        Args:
            plan: LayawayPlan to generate contract for
            contract_template: Contract template to use
            
        Returns:
            PDF file content as bytes
        """
        if contract_template is None:
            contract_template = LayawayContract.objects.filter(
                is_default=True, is_active=True
            ).first()
        
        if not contract_template:
            raise ValidationError("No contract template available")
        
        # Generate contract content
        contract_content = contract_template.generate_contract(plan)
        
        # TODO: Implement PDF generation with Persian support
        # For now, return the text content
        return contract_content.encode('utf-8')
    
    @staticmethod
    def create_default_contract_template():
        """Create default Persian layaway contract template."""
        default_template = """
قرارداد طلای قرضی

شماره قرارداد: {{plan_number}}
تاریخ: {{contract_date}}

طرف اول (فروشنده): فروشگاه طلا و جواهر
طرف دوم (خریدار): {{customer_name}}
شماره تماس: {{customer_phone}}
آدرس: {{customer_address}}

مشخصات کالا:
نام کالا: {{jewelry_item}}
کد کالا: {{jewelry_sku}}

شرایط مالی:
مبلغ کل: {{total_amount}} تومان
پیش پرداخت: {{down_payment}} تومان
مبلغ هر قسط: {{installment_amount}} تومان
تعداد اقساط: {{number_of_payments}}
دوره پرداخت: {{payment_frequency}}
تاریخ شروع: {{start_date}}
تاریخ پایان: {{expected_completion}}

شرایط و ضوابط:
1. مهلت نسیه هر قسط {{grace_period}} روز می‌باشد.
2. در صورت تاخیر در پرداخت، {{late_fee_percentage}}% جریمه تاخیر اعمال می‌شود.
3. در صورت لغو قرارداد، {{cancellation_fee_percentage}}% کسر می‌گردد.
4. کالا تا تسویه کامل نزد فروشنده باقی می‌ماند.

امضای طرفین:
فروشنده: ________________
خریدار: ________________

تاریخ: {{contract_date}}
        """.strip()
        
        contract, created = LayawayContract.objects.get_or_create(
            name='قرارداد استاندارد طلای قرضی',
            defaults={
                'contract_type': 'standard',
                'persian_title': 'قرارداد طلای قرضی',
                'contract_template': default_template,
                'is_default': True,
                'is_active': True
            }
        )
        
        return contract


class LayawayReportService:
    """
    Service class for layaway reporting and analytics.
    """
    
    @staticmethod
    def get_layaway_summary(start_date: date = None, end_date: date = None) -> Dict:
        """
        Get summary statistics for layaway plans.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dictionary with summary statistics
        """
        queryset = LayawayPlan.objects.all()
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Calculate statistics
        total_plans = queryset.count()
        active_plans = queryset.filter(status='active').count()
        completed_plans = queryset.filter(status='completed').count()
        cancelled_plans = queryset.filter(status='cancelled').count()
        
        # Financial statistics
        total_value = sum(plan.total_amount for plan in queryset)
        total_collected = sum(plan.total_paid for plan in queryset)
        outstanding_balance = sum(plan.remaining_balance for plan in queryset.filter(status='active'))
        
        # Overdue statistics
        overdue_plans = LayawayPlanService.get_overdue_plans()
        overdue_count = len(overdue_plans)
        overdue_amount = sum(plan.remaining_balance for plan in overdue_plans)
        
        return {
            'total_plans': total_plans,
            'active_plans': active_plans,
            'completed_plans': completed_plans,
            'cancelled_plans': cancelled_plans,
            'completion_rate': (completed_plans / total_plans * 100) if total_plans > 0 else 0,
            'total_value': total_value,
            'total_collected': total_collected,
            'outstanding_balance': outstanding_balance,
            'collection_rate': (total_collected / total_value * 100) if total_value > 0 else 0,
            'overdue_count': overdue_count,
            'overdue_amount': overdue_amount,
            'overdue_rate': (overdue_count / active_plans * 100) if active_plans > 0 else 0,
        }
    
    @staticmethod
    def get_customer_layaway_history(customer: Customer) -> Dict:
        """
        Get layaway history for a specific customer.
        
        Args:
            customer: Customer to get history for
            
        Returns:
            Dictionary with customer layaway history
        """
        plans = customer.layaway_plans.all().order_by('-created_at')
        
        return {
            'total_plans': plans.count(),
            'active_plans': plans.filter(status='active').count(),
            'completed_plans': plans.filter(status='completed').count(),
            'cancelled_plans': plans.filter(status='cancelled').count(),
            'total_purchased': sum(plan.total_amount for plan in plans.filter(status='completed')),
            'current_balance': sum(plan.remaining_balance for plan in plans.filter(status='active')),
            'payment_history': [
                {
                    'plan_number': plan.plan_number,
                    'jewelry_item': plan.jewelry_item.name,
                    'total_amount': plan.total_amount,
                    'status': plan.get_status_display(),
                    'completion_percentage': plan.completion_percentage,
                    'created_date': plan.created_at.date()
                }
                for plan in plans
            ]
        }