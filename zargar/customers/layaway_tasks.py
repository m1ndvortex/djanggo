"""
Celery tasks for layaway and installment plan management.
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from datetime import timedelta
import logging

from .layaway_models import LayawayPlan, LayawayReminder, LayawayScheduledPayment
from .layaway_services import LayawayReminderService, LayawayPlanService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_payment_reminders(self):
    """
    Send payment reminders for upcoming and overdue layaway payments.
    
    This task runs daily to:
    1. Send upcoming payment reminders (3 days before due date)
    2. Send overdue payment reminders
    3. Update overdue status for scheduled payments
    """
    try:
        # Send upcoming payment reminders
        upcoming_sent = LayawayReminderService.send_upcoming_reminders()
        
        # Send overdue payment reminders
        overdue_sent = LayawayReminderService.send_overdue_reminders()
        
        # Update overdue status for scheduled payments
        update_overdue_status.delay()
        
        logger.info(
            f"Payment reminders sent - Upcoming: {upcoming_sent}, Overdue: {overdue_sent}"
        )
        
        return {
            'status': 'success',
            'upcoming_reminders_sent': upcoming_sent,
            'overdue_reminders_sent': overdue_sent
        }
        
    except Exception as exc:
        logger.error(f"Error sending payment reminders: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 5)  # Retry after 5 minutes


@shared_task(bind=True, max_retries=3)
def update_overdue_status(self):
    """
    Update overdue status for scheduled payments and apply late fees.
    """
    try:
        today = timezone.now().date()
        updated_count = 0
        
        # Get all unpaid scheduled payments that are past due date + grace period
        overdue_payments = LayawayScheduledPayment.objects.filter(
            is_paid=False,
            is_overdue=False,
            due_date__lt=today
        ).select_related('layaway_plan')
        
        for payment in overdue_payments:
            grace_period_end = payment.due_date + timedelta(
                days=payment.layaway_plan.grace_period_days
            )
            
            if today > grace_period_end:
                # Mark as overdue
                payment.is_overdue = True
                
                # Apply late fee if configured
                plan = payment.layaway_plan
                if hasattr(plan, 'late_payment_fee') and plan.late_payment_fee > 0:
                    # Calculate late fee (percentage of payment amount)
                    late_fee = (payment.amount * plan.late_payment_fee) / 100
                    payment.late_fee_applied = late_fee
                    
                    # Add to plan's total late fees
                    plan.late_payment_fee += late_fee
                    plan.save(update_fields=['late_payment_fee'])
                
                payment.save(update_fields=['is_overdue', 'late_fee_applied'])
                updated_count += 1
        
        logger.info(f"Updated overdue status for {updated_count} payments")
        
        return {
            'status': 'success',
            'payments_marked_overdue': updated_count
        }
        
    except Exception as exc:
        logger.error(f"Error updating overdue status: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 10)  # Retry after 10 minutes


@shared_task(bind=True, max_retries=3)
def generate_layaway_contract(self, plan_id, email_to_customer=False):
    """
    Generate layaway contract PDF and optionally email to customer.
    
    Args:
        plan_id: LayawayPlan ID
        email_to_customer: Whether to email contract to customer
    """
    try:
        from .layaway_services import LayawayContractService
        
        plan = LayawayPlan.objects.get(id=plan_id)
        
        # Generate contract content
        contract_content = LayawayContractService.generate_contract_pdf(plan)
        
        # Save contract content (in a real implementation, save to file storage)
        # For now, we'll just log the generation
        logger.info(f"Contract generated for plan {plan.plan_number}")
        
        # Email to customer if requested
        if email_to_customer and plan.customer.email:
            send_contract_email.delay(plan_id, contract_content.decode('utf-8'))
        
        return {
            'status': 'success',
            'plan_number': plan.plan_number,
            'contract_generated': True,
            'emailed_to_customer': email_to_customer and bool(plan.customer.email)
        }
        
    except LayawayPlan.DoesNotExist:
        logger.error(f"LayawayPlan with ID {plan_id} not found")
        return {'status': 'error', 'message': 'Plan not found'}
        
    except Exception as exc:
        logger.error(f"Error generating contract for plan {plan_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 2)  # Retry after 2 minutes


@shared_task(bind=True, max_retries=3)
def send_contract_email(self, plan_id, contract_content):
    """
    Send layaway contract via email to customer.
    
    Args:
        plan_id: LayawayPlan ID
        contract_content: Contract content as string
    """
    try:
        plan = LayawayPlan.objects.get(id=plan_id)
        
        if not plan.customer.email:
            logger.warning(f"No email address for customer in plan {plan.plan_number}")
            return {'status': 'error', 'message': 'No customer email'}
        
        # Prepare email content
        subject = f'قرارداد طلای قرضی - {plan.plan_number}'
        
        # Render email template
        email_body = render_to_string('customers/emails/layaway_contract.html', {
            'plan': plan,
            'customer': plan.customer,
            'contract_content': contract_content
        })
        
        # Send email
        send_mail(
            subject=subject,
            message=contract_content,  # Plain text version
            html_message=email_body,   # HTML version
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[plan.customer.email],
            fail_silently=False
        )
        
        logger.info(f"Contract emailed to customer for plan {plan.plan_number}")
        
        return {
            'status': 'success',
            'plan_number': plan.plan_number,
            'email_sent': True,
            'recipient': plan.customer.email
        }
        
    except LayawayPlan.DoesNotExist:
        logger.error(f"LayawayPlan with ID {plan_id} not found")
        return {'status': 'error', 'message': 'Plan not found'}
        
    except Exception as exc:
        logger.error(f"Error sending contract email for plan {plan_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 5)  # Retry after 5 minutes


@shared_task(bind=True, max_retries=3)
def process_automatic_plan_completion(self):
    """
    Check for plans that should be automatically completed.
    """
    try:
        completed_count = 0
        
        # Find plans that are fully paid but not marked as completed
        active_plans = LayawayPlan.objects.filter(status='active')
        
        for plan in active_plans:
            if plan.remaining_balance <= 0.01:  # Essentially zero with decimal precision
                plan.complete_plan()
                completed_count += 1
                logger.info(f"Auto-completed plan {plan.plan_number}")
        
        return {
            'status': 'success',
            'plans_completed': completed_count
        }
        
    except Exception as exc:
        logger.error(f"Error in automatic plan completion: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 10)


@shared_task(bind=True, max_retries=3)
def send_completion_notifications(self):
    """
    Send notifications for recently completed layaway plans.
    """
    try:
        from datetime import timedelta
        
        # Find plans completed in the last 24 hours
        yesterday = timezone.now() - timedelta(days=1)
        recently_completed = LayawayPlan.objects.filter(
            status='completed',
            actual_completion_date__gte=yesterday.date()
        )
        
        notifications_sent = 0
        
        for plan in recently_completed:
            # Check if completion notification already sent
            existing_notification = plan.reminders.filter(
                reminder_type='completion',
                is_sent=True
            ).exists()
            
            if not existing_notification:
                # Create and send completion notification
                reminder = LayawayReminder.objects.create(
                    layaway_plan=plan,
                    reminder_type='completion',
                    scheduled_date=timezone.now().date(),
                    delivery_method='sms',
                    recipient=plan.customer.phone_number,
                    message_template=_get_completion_message_template()
                )
                
                if reminder.send_reminder():
                    notifications_sent += 1
        
        logger.info(f"Sent {notifications_sent} completion notifications")
        
        return {
            'status': 'success',
            'notifications_sent': notifications_sent
        }
        
    except Exception as exc:
        logger.error(f"Error sending completion notifications: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 5)


@shared_task(bind=True, max_retries=3)
def generate_layaway_reports(self):
    """
    Generate daily layaway reports and statistics.
    """
    try:
        from .layaway_services import LayawayReportService
        
        # Generate summary statistics
        summary = LayawayReportService.get_layaway_summary()
        
        # Log key metrics
        logger.info(f"Daily layaway report - Active plans: {summary['active_plans']}, "
                   f"Overdue: {summary['overdue_count']}, "
                   f"Collection rate: {summary['collection_rate']:.2f}%")
        
        # TODO: Save report to database or send to management
        
        return {
            'status': 'success',
            'report_generated': True,
            'summary': summary
        }
        
    except Exception as exc:
        logger.error(f"Error generating layaway reports: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 15)


@shared_task(bind=True, max_retries=3)
def cleanup_old_reminders(self):
    """
    Clean up old reminder records to prevent database bloat.
    """
    try:
        from datetime import timedelta
        
        # Delete reminders older than 6 months
        cutoff_date = timezone.now() - timedelta(days=180)
        
        deleted_count = LayawayReminder.objects.filter(
            created_at__lt=cutoff_date,
            is_sent=True
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old reminder records")
        
        return {
            'status': 'success',
            'reminders_deleted': deleted_count
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up old reminders: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 30)


@shared_task(bind=True, max_retries=3)
def send_weekly_layaway_summary(self):
    """
    Send weekly summary report to management.
    """
    try:
        from .layaway_services import LayawayReportService
        from datetime import timedelta
        
        # Generate weekly summary
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        summary = LayawayReportService.get_layaway_summary(start_date, end_date)
        
        # Prepare email content
        subject = f'گزارش هفتگی طلای قرضی - {start_date} تا {end_date}'
        
        email_body = render_to_string('customers/emails/weekly_layaway_summary.html', {
            'summary': summary,
            'start_date': start_date,
            'end_date': end_date
        })
        
        # Send to management (configure recipient emails in settings)
        management_emails = getattr(settings, 'LAYAWAY_REPORT_RECIPIENTS', [])
        
        if management_emails:
            send_mail(
                subject=subject,
                message=f"Weekly layaway summary report",
                html_message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=management_emails,
                fail_silently=False
            )
        
        logger.info("Weekly layaway summary sent to management")
        
        return {
            'status': 'success',
            'report_sent': True,
            'recipients': len(management_emails)
        }
        
    except Exception as exc:
        logger.error(f"Error sending weekly summary: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * 10)


def _get_completion_message_template():
    """Get template for plan completion notification."""
    return """
تبریک {{customer_name}} عزیز!

طلای قرضی شما با موفقیت تکمیل شد:
شماره قرارداد: {{plan_number}}
نام کالا: {{jewelry_item}}

برای تحویل کالا به فروشگاه مراجعه فرمایید.

با تشکر از اعتماد شما
    """.strip()


# Periodic task configuration (add to celery beat schedule)
"""
Add to CELERY_BEAT_SCHEDULE in settings:

'send-layaway-reminders': {
    'task': 'zargar.customers.layaway_tasks.send_payment_reminders',
    'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
},
'update-overdue-status': {
    'task': 'zargar.customers.layaway_tasks.update_overdue_status',
    'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
},
'process-plan-completion': {
    'task': 'zargar.customers.layaway_tasks.process_automatic_plan_completion',
    'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
},
'send-completion-notifications': {
    'task': 'zargar.customers.layaway_tasks.send_completion_notifications',
    'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
},
'generate-layaway-reports': {
    'task': 'zargar.customers.layaway_tasks.generate_layaway_reports',
    'schedule': crontab(hour=23, minute=0),  # Daily at 11 PM
},
'cleanup-old-reminders': {
    'task': 'zargar.customers.layaway_tasks.cleanup_old_reminders',
    'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Weekly on Sunday at 3 AM
},
'send-weekly-summary': {
    'task': 'zargar.customers.layaway_tasks.send_weekly_layaway_summary',
    'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Weekly on Monday at 8 AM
},
"""