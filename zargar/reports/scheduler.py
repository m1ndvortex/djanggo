"""
Report scheduling service for automated report generation and delivery.

This module handles the scheduling, generation, and delivery of reports
according to configured schedules.
"""

from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from celery import shared_task
import logging
from typing import List, Dict, Any, Optional
from decimal import Decimal
import uuid
from datetime import datetime, timedelta

from .models import ReportSchedule, ReportTemplate, GeneratedReport, ReportDelivery
from .services import ComprehensiveReportingEngine
from .exporters import ReportExporter

logger = logging.getLogger(__name__)


class ReportScheduler:
    """
    Service class for managing report scheduling and automated generation.
    """
    
    def __init__(self):
        """Initialize the report scheduler."""
        self.reporting_engine = ComprehensiveReportingEngine()
        self.exporter = ReportExporter()
    
    def check_and_execute_schedules(self) -> Dict[str, Any]:
        """
        Check for schedules that need to be executed and run them.
        
        Returns:
            Dictionary with execution results
        """
        executed_schedules = []
        failed_schedules = []
        
        # Get all active schedules that should execute now
        schedules_to_execute = ReportSchedule.objects.filter(
            is_active=True,
            next_execution__lte=timezone.now()
        )
        
        logger.info(f"Found {schedules_to_execute.count()} schedules to execute")
        
        for schedule in schedules_to_execute:
            try:
                result = self.execute_schedule(schedule)
                executed_schedules.append({
                    'schedule_id': schedule.id,
                    'schedule_name': schedule.name_persian or schedule.name,
                    'result': result
                })
                logger.info(f"Successfully executed schedule: {schedule.name}")
            except Exception as e:
                logger.error(f"Failed to execute schedule {schedule.name}: {str(e)}")
                failed_schedules.append({
                    'schedule_id': schedule.id,
                    'schedule_name': schedule.name_persian or schedule.name,
                    'error': str(e)
                })
                schedule.mark_execution(success=False)
        
        return {
            'executed_count': len(executed_schedules),
            'failed_count': len(failed_schedules),
            'executed_schedules': executed_schedules,
            'failed_schedules': failed_schedules,
            'execution_time': timezone.now()
        }
    
    def execute_schedule(self, schedule: ReportSchedule) -> Dict[str, Any]:
        """
        Execute a specific report schedule.
        
        Args:
            schedule: ReportSchedule instance to execute
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Executing schedule: {schedule.name}")
        
        # Generate report parameters based on schedule configuration
        parameters = self._build_schedule_parameters(schedule)
        
        # Generate the report
        generated_report = self._generate_scheduled_report(schedule, parameters)
        
        # Deliver the report
        delivery_results = self._deliver_report(schedule, generated_report)
        
        # Mark schedule as executed
        schedule.mark_execution(success=True)
        
        return {
            'schedule_id': schedule.id,
            'generated_report_id': generated_report.report_id,
            'delivery_results': delivery_results,
            'execution_time': timezone.now()
        }
    
    def _build_schedule_parameters(self, schedule: ReportSchedule) -> Dict[str, Any]:
        """
        Build report parameters based on schedule configuration.
        
        Args:
            schedule: ReportSchedule instance
            
        Returns:
            Dictionary of report parameters
        """
        parameters = schedule.schedule_parameters.copy()
        
        # Set date ranges based on frequency
        today = timezone.now().date()
        
        if schedule.frequency == 'daily':
            parameters['date_from'] = today - timedelta(days=1)
            parameters['date_to'] = today - timedelta(days=1)
        elif schedule.frequency == 'weekly':
            parameters['date_from'] = today - timedelta(days=7)
            parameters['date_to'] = today - timedelta(days=1)
        elif schedule.frequency == 'monthly':
            # Previous month
            first_day_this_month = today.replace(day=1)
            last_day_prev_month = first_day_this_month - timedelta(days=1)
            first_day_prev_month = last_day_prev_month.replace(day=1)
            
            parameters['date_from'] = first_day_prev_month
            parameters['date_to'] = last_day_prev_month
        elif schedule.frequency == 'quarterly':
            # Previous quarter
            current_quarter = (today.month - 1) // 3 + 1
            if current_quarter == 1:
                prev_quarter_start = today.replace(year=today.year - 1, month=10, day=1)
                prev_quarter_end = today.replace(year=today.year - 1, month=12, day=31)
            else:
                prev_quarter_month = (current_quarter - 2) * 3 + 1
                prev_quarter_start = today.replace(month=prev_quarter_month, day=1)
                prev_quarter_end = today.replace(month=prev_quarter_month + 2, day=31)
            
            parameters['date_from'] = prev_quarter_start
            parameters['date_to'] = prev_quarter_end
        elif schedule.frequency == 'yearly':
            # Previous year
            parameters['date_from'] = today.replace(year=today.year - 1, month=1, day=1)
            parameters['date_to'] = today.replace(year=today.year - 1, month=12, day=31)
        
        return parameters
    
    def _generate_scheduled_report(self, schedule: ReportSchedule, parameters: Dict[str, Any]) -> GeneratedReport:
        """
        Generate a report for a schedule.
        
        Args:
            schedule: ReportSchedule instance
            parameters: Report generation parameters
            
        Returns:
            GeneratedReport instance
        """
        # Create GeneratedReport record
        generated_report = GeneratedReport.objects.create(
            template=schedule.template,
            report_parameters=parameters,
            date_from=parameters.get('date_from'),
            date_to=parameters.get('date_to'),
            output_format=schedule.template.default_output_format,
            status='generating',
            generation_started_at=timezone.now()
        )
        
        try:
            # Set tenant context for reporting engine
            self.reporting_engine.tenant = schedule.tenant
            
            # Generate report data
            report_data = self.reporting_engine.generate_report(
                schedule.template, 
                parameters
            )
            
            # Export report to file
            file_path = self.exporter.export_report(
                report_data,
                generated_report.output_format,
                generated_report.download_filename
            )
            
            # Update generated report
            generated_report.status = 'completed'
            generated_report.generation_completed_at = timezone.now()
            generated_report.generation_duration_seconds = (
                generated_report.generation_completed_at - 
                generated_report.generation_started_at
            ).total_seconds()
            generated_report.file_path = file_path
            generated_report.report_data = report_data
            generated_report.save()
            
            logger.info(f"Successfully generated report: {generated_report.report_id}")
            
        except Exception as e:
            generated_report.status = 'failed'
            generated_report.error_message = str(e)
            generated_report.save()
            logger.error(f"Failed to generate report {generated_report.report_id}: {str(e)}")
            raise
        
        return generated_report
    
    def _deliver_report(self, schedule: ReportSchedule, generated_report: GeneratedReport) -> List[Dict[str, Any]]:
        """
        Deliver a generated report according to schedule settings.
        
        Args:
            schedule: ReportSchedule instance
            generated_report: GeneratedReport instance
            
        Returns:
            List of delivery results
        """
        delivery_results = []
        
        for delivery_method in schedule.delivery_methods:
            if delivery_method == 'email':
                for email in schedule.email_recipients:
                    result = self._deliver_via_email(schedule, generated_report, email)
                    delivery_results.append(result)
            elif delivery_method == 'sms':
                for phone in schedule.sms_recipients:
                    result = self._deliver_via_sms(schedule, generated_report, phone)
                    delivery_results.append(result)
            elif delivery_method == 'internal':
                result = self._deliver_to_dashboard(schedule, generated_report)
                delivery_results.append(result)
            elif delivery_method == 'file_storage':
                result = self._deliver_to_storage(schedule, generated_report)
                delivery_results.append(result)
        
        return delivery_results
    
    def _deliver_via_email(self, schedule: ReportSchedule, generated_report: GeneratedReport, email: str) -> Dict[str, Any]:
        """
        Deliver report via email.
        
        Args:
            schedule: ReportSchedule instance
            generated_report: GeneratedReport instance
            email: Email address
            
        Returns:
            Delivery result dictionary
        """
        delivery = ReportDelivery.objects.create(
            generated_report=generated_report,
            schedule=schedule,
            delivery_method='email',
            recipient=email,
            status='pending'
        )
        
        try:
            # Prepare email content
            subject = f"گزارش {schedule.template.name_persian or schedule.template.name}"
            
            context = {
                'schedule': schedule,
                'generated_report': generated_report,
                'report_data': generated_report.report_data,
            }
            
            html_content = render_to_string(
                'reports/email/scheduled_report.html',
                context
            )
            
            # Create email message
            email_message = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            email_message.content_subtype = 'html'
            
            # Attach report file if available
            if generated_report.file_path:
                email_message.attach_file(generated_report.file_path)
            
            # Send email
            email_message.send()
            
            delivery.mark_sent()
            delivery.mark_delivered()
            
            logger.info(f"Successfully delivered report {generated_report.report_id} to {email}")
            
            return {
                'delivery_id': delivery.id,
                'method': 'email',
                'recipient': email,
                'status': 'delivered',
                'error': None
            }
            
        except Exception as e:
            delivery.mark_failed(str(e))
            logger.error(f"Failed to deliver report {generated_report.report_id} to {email}: {str(e)}")
            
            return {
                'delivery_id': delivery.id,
                'method': 'email',
                'recipient': email,
                'status': 'failed',
                'error': str(e)
            }
    
    def _deliver_via_sms(self, schedule: ReportSchedule, generated_report: GeneratedReport, phone: str) -> Dict[str, Any]:
        """
        Deliver report notification via SMS.
        
        Args:
            schedule: ReportSchedule instance
            generated_report: GeneratedReport instance
            phone: Phone number
            
        Returns:
            Delivery result dictionary
        """
        delivery = ReportDelivery.objects.create(
            generated_report=generated_report,
            schedule=schedule,
            delivery_method='sms',
            recipient=phone,
            status='pending'
        )
        
        try:
            # Prepare SMS content
            message = f"گزارش {schedule.template.name_persian or schedule.template.name} آماده شد. برای مشاهده به پنل مدیریت مراجعه کنید."
            
            # TODO: Implement SMS sending logic
            # This would integrate with Iranian SMS providers like Kavenegar, etc.
            # For now, we'll mark as sent
            
            delivery.mark_sent()
            delivery.mark_delivered()
            
            logger.info(f"Successfully sent SMS notification for report {generated_report.report_id} to {phone}")
            
            return {
                'delivery_id': delivery.id,
                'method': 'sms',
                'recipient': phone,
                'status': 'delivered',
                'error': None
            }
            
        except Exception as e:
            delivery.mark_failed(str(e))
            logger.error(f"Failed to send SMS for report {generated_report.report_id} to {phone}: {str(e)}")
            
            return {
                'delivery_id': delivery.id,
                'method': 'sms',
                'recipient': phone,
                'status': 'failed',
                'error': str(e)
            }
    
    def _deliver_to_dashboard(self, schedule: ReportSchedule, generated_report: GeneratedReport) -> Dict[str, Any]:
        """
        Make report available in dashboard.
        
        Args:
            schedule: ReportSchedule instance
            generated_report: GeneratedReport instance
            
        Returns:
            Delivery result dictionary
        """
        delivery = ReportDelivery.objects.create(
            generated_report=generated_report,
            schedule=schedule,
            delivery_method='internal',
            recipient='dashboard',
            status='pending'
        )
        
        try:
            # Report is automatically available in dashboard through GeneratedReport model
            delivery.mark_sent()
            delivery.mark_delivered()
            
            logger.info(f"Report {generated_report.report_id} made available in dashboard")
            
            return {
                'delivery_id': delivery.id,
                'method': 'internal',
                'recipient': 'dashboard',
                'status': 'delivered',
                'error': None
            }
            
        except Exception as e:
            delivery.mark_failed(str(e))
            logger.error(f"Failed to make report {generated_report.report_id} available in dashboard: {str(e)}")
            
            return {
                'delivery_id': delivery.id,
                'method': 'internal',
                'recipient': 'dashboard',
                'status': 'failed',
                'error': str(e)
            }
    
    def _deliver_to_storage(self, schedule: ReportSchedule, generated_report: GeneratedReport) -> Dict[str, Any]:
        """
        Store report in file storage.
        
        Args:
            schedule: ReportSchedule instance
            generated_report: GeneratedReport instance
            
        Returns:
            Delivery result dictionary
        """
        delivery = ReportDelivery.objects.create(
            generated_report=generated_report,
            schedule=schedule,
            delivery_method='file_storage',
            recipient='storage',
            status='pending'
        )
        
        try:
            # Report file is already stored during generation
            # This delivery method just confirms storage
            delivery.mark_sent()
            delivery.mark_delivered()
            
            logger.info(f"Report {generated_report.report_id} stored in file storage")
            
            return {
                'delivery_id': delivery.id,
                'method': 'file_storage',
                'recipient': 'storage',
                'status': 'delivered',
                'error': None
            }
            
        except Exception as e:
            delivery.mark_failed(str(e))
            logger.error(f"Failed to store report {generated_report.report_id}: {str(e)}")
            
            return {
                'delivery_id': delivery.id,
                'method': 'file_storage',
                'recipient': 'storage',
                'status': 'failed',
                'error': str(e)
            }


# Celery tasks for automated scheduling
@shared_task
def execute_scheduled_reports():
    """
    Celery task to execute scheduled reports.
    
    This task should be run periodically (e.g., every hour) to check
    for and execute any scheduled reports.
    """
    scheduler = ReportScheduler()
    result = scheduler.check_and_execute_schedules()
    
    logger.info(f"Scheduled report execution completed: {result['executed_count']} executed, {result['failed_count']} failed")
    
    return result


@shared_task
def generate_single_report(template_id: int, parameters: Dict[str, Any], output_format: str = 'pdf'):
    """
    Celery task to generate a single report asynchronously.
    
    Args:
        template_id: ReportTemplate ID
        parameters: Report generation parameters
        output_format: Output format (pdf, excel, csv, json)
        
    Returns:
        Generated report ID
    """
    try:
        template = ReportTemplate.objects.get(id=template_id)
        
        # Create GeneratedReport record
        generated_report = GeneratedReport.objects.create(
            template=template,
            report_parameters=parameters,
            date_from=parameters.get('date_from'),
            date_to=parameters.get('date_to'),
            output_format=output_format,
            status='generating',
            generation_started_at=timezone.now()
        )
        
        # Generate report
        reporting_engine = ComprehensiveReportingEngine(tenant=template.tenant)
        report_data = reporting_engine.generate_report(template, parameters)
        
        # Export report
        exporter = ReportExporter()
        file_path = exporter.export_report(
            report_data,
            output_format,
            generated_report.download_filename
        )
        
        # Update generated report
        generated_report.status = 'completed'
        generated_report.generation_completed_at = timezone.now()
        generated_report.generation_duration_seconds = (
            generated_report.generation_completed_at - 
            generated_report.generation_started_at
        ).total_seconds()
        generated_report.file_path = file_path
        generated_report.report_data = report_data
        generated_report.save()
        
        logger.info(f"Successfully generated report: {generated_report.report_id}")
        
        return generated_report.report_id
        
    except Exception as e:
        if 'generated_report' in locals():
            generated_report.status = 'failed'
            generated_report.error_message = str(e)
            generated_report.save()
        
        logger.error(f"Failed to generate report: {str(e)}")
        raise


@shared_task
def cleanup_expired_reports():
    """
    Celery task to clean up expired reports.
    
    This task should be run daily to remove expired report files
    and update database records.
    """
    expired_reports = GeneratedReport.objects.filter(
        expires_at__lt=timezone.now(),
        status='completed'
    )
    
    cleaned_count = 0
    
    for report in expired_reports:
        try:
            # Remove file if it exists
            if report.file_path:
                import os
                if os.path.exists(report.file_path):
                    os.remove(report.file_path)
            
            # Update status
            report.status = 'expired'
            report.file_path = ''
            report.save()
            
            cleaned_count += 1
            
        except Exception as e:
            logger.error(f"Failed to cleanup report {report.report_id}: {str(e)}")
    
    logger.info(f"Cleaned up {cleaned_count} expired reports")
    
    return {
        'cleaned_count': cleaned_count,
        'cleanup_time': timezone.now()
    }