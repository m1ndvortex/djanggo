"""
Push notification system views for zargar project.
"""
import json
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.forms import ModelForm, CharField, Textarea, MultipleChoiceField, CheckboxSelectMultiple

from .notification_models import (
    NotificationTemplate, 
    NotificationSchedule, 
    Notification, 
    NotificationDeliveryLog,
    NotificationProvider
)
from .notification_services import PushNotificationSystem, NotificationScheduler
from zargar.customers.models import Customer
from zargar.core.models import User


class NotificationTemplateForm(ModelForm):
    """Form for creating/editing notification templates."""
    
    delivery_methods = MultipleChoiceField(
        choices=[
            ('sms', _('SMS')),
            ('email', _('Email')),
            ('push', _('Push Notification')),
            ('whatsapp', _('WhatsApp')),
        ],
        widget=CheckboxSelectMultiple,
        required=True,
        label=_('Delivery Methods')
    )
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'template_type', 'title', 'content', 
            'delivery_methods', 'is_active', 'is_default'
        ]
        widgets = {
            'content': Textarea(attrs={
                'rows': 5, 
                'class': 'form-control persian-textarea',
                'placeholder': _('Enter Persian message template with variables like {customer_name}, {amount}, etc.')
            }),
            'title': CharField(widget=Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': _('Message title for email/push notifications')
            }))
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial delivery methods from JSON field
        if self.instance and self.instance.pk:
            self.fields['delivery_methods'].initial = self.instance.delivery_methods or []
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Convert delivery methods to JSON
        instance.delivery_methods = self.cleaned_data['delivery_methods']
        
        # Set default available variables based on template type
        template_type = instance.template_type
        if template_type == 'payment_reminder':
            instance.available_variables = {
                'customer_name': _('Customer Name'),
                'contract_number': _('Contract Number'),
                'amount': _('Payment Amount'),
                'due_date': _('Due Date'),
                'remaining_weight': _('Remaining Gold Weight'),
            }
        elif template_type == 'birthday_greeting':
            instance.available_variables = {
                'customer_name': _('Customer Name'),
                'birth_date': _('Birth Date'),
                'age': _('Age'),
            }
        elif template_type == 'appointment_reminder':
            instance.available_variables = {
                'customer_name': _('Customer Name'),
                'appointment_date': _('Appointment Date'),
                'appointment_time': _('Appointment Time'),
                'service_type': _('Service Type'),
            }
        elif template_type == 'special_offer':
            instance.available_variables = {
                'customer_name': _('Customer Name'),
                'offer_title': _('Offer Title'),
                'offer_description': _('Offer Description'),
                'discount_percentage': _('Discount Percentage'),
                'expiry_date': _('Expiry Date'),
            }
        else:
            instance.available_variables = {
                'customer_name': _('Customer Name'),
                'date': _('Current Date'),
                'shop_name': _('Shop Name'),
            }
        
        if commit:
            instance.save()
        return instance


@method_decorator(login_required, name='dispatch')
class NotificationDashboardView(ListView):
    """Main notification management dashboard."""
    
    template_name = 'core/notifications/dashboard.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        """Get recent notifications with filters."""
        queryset = Notification.objects.select_related('template').order_by('-created_at')
        
        # Apply filters
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        method_filter = self.request.GET.get('method')
        if method_filter:
            queryset = queryset.filter(delivery_method=method_filter)
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(recipient_name__icontains=search_query) |
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get notification statistics
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        context['notification_stats'] = {
            'total_notifications': Notification.objects.count(),
            'pending_notifications': Notification.objects.filter(status='pending').count(),
            'sent_today': Notification.objects.filter(
                status='sent',
                sent_at__gte=today_start
            ).count(),
            'failed_today': Notification.objects.filter(
                status='failed',
                failed_at__gte=today_start
            ).count(),
            'scheduled_notifications': Notification.objects.filter(
                status__in=['pending', 'queued'],
                scheduled_at__gt=now
            ).count(),
        }
        
        # Get templates for quick actions
        context['notification_templates'] = NotificationTemplate.objects.filter(
            is_active=True
        ).order_by('template_type', 'name')
        
        # Get recent delivery logs
        context['recent_logs'] = NotificationDeliveryLog.objects.select_related(
            'notification'
        ).order_by('-timestamp')[:10]
        
        return context


@method_decorator(login_required, name='dispatch')
class NotificationTemplateListView(ListView):
    """List all notification templates."""
    
    model = NotificationTemplate
    template_name = 'core/notifications/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20
    
    def get_queryset(self):
        return NotificationTemplate.objects.order_by('template_type', 'name')


@method_decorator(login_required, name='dispatch')
class NotificationTemplateCreateView(CreateView):
    """Create new notification template."""
    
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'core/notifications/template_form.html'
    success_url = reverse_lazy('core:notification_template_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Notification template created successfully.'))
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class NotificationTemplateUpdateView(UpdateView):
    """Update notification template."""
    
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'core/notifications/template_form.html'
    success_url = reverse_lazy('core:notification_template_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Notification template updated successfully.'))
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class NotificationTemplateDeleteView(DeleteView):
    """Delete notification template."""
    
    model = NotificationTemplate
    template_name = 'core/notifications/template_confirm_delete.html'
    success_url = reverse_lazy('core:notification_template_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Notification template deleted successfully.'))
        return super().delete(request, *args, **kwargs)


@login_required
def notification_history_view(request):
    """View notification history with detailed logs."""
    
    # Get notifications with pagination
    notifications = Notification.objects.select_related('template').order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        notifications = notifications.filter(status=status_filter)
    
    method_filter = request.GET.get('method')
    if method_filter:
        notifications = notifications.filter(delivery_method=method_filter)
    
    date_from = request.GET.get('date_from')
    if date_from:
        notifications = notifications.filter(created_at__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        notifications = notifications.filter(created_at__lte=date_to)
    
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'notifications': page_obj.object_list,
        'status_choices': Notification.STATUS_CHOICES,
        'method_choices': Notification.DELIVERY_METHODS,
    }
    
    return render(request, 'core/notifications/history.html', context)


@login_required
def notification_detail_view(request, notification_id):
    """View detailed notification information and logs."""
    
    notification = get_object_or_404(Notification, id=notification_id)
    delivery_logs = notification.delivery_logs.order_by('-timestamp')
    
    context = {
        'notification': notification,
        'delivery_logs': delivery_logs,
    }
    
    return render(request, 'core/notifications/detail.html', context)


@login_required
@require_http_methods(["POST"])
def send_notification_ajax(request):
    """Send notification via AJAX."""
    
    try:
        data = json.loads(request.body)
        
        template_type = data.get('template_type')
        recipient_type = data.get('recipient_type', 'customer')
        recipient_id = data.get('recipient_id')
        context = data.get('context', {})
        delivery_methods = data.get('delivery_methods', ['sms'])
        
        if not all([template_type, recipient_id]):
            return JsonResponse({
                'success': False,
                'error': _('Missing required fields')
            })
        
        # Create and send notification
        system = PushNotificationSystem()
        notifications = system.create_notification(
            template_type=template_type,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            context=context,
            delivery_methods=delivery_methods
        )
        
        # Send immediately
        sent_count = 0
        for notification in notifications:
            if system.send_notification(notification):
                sent_count += 1
        
        return JsonResponse({
            'success': True,
            'message': _('Notification sent successfully'),
            'notifications_created': len(notifications),
            'notifications_sent': sent_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def send_bulk_notifications_ajax(request):
    """Send bulk notifications via AJAX."""
    
    try:
        data = json.loads(request.body)
        
        template_type = data.get('template_type')
        target_type = data.get('target_type', 'selected')
        selected_ids = data.get('selected_ids', [])
        context_template = data.get('context', {})
        delivery_methods = data.get('delivery_methods', ['sms'])
        
        if not template_type:
            return JsonResponse({
                'success': False,
                'error': _('Template type is required')
            })
        
        # Get recipients based on target type
        recipients = []
        
        if target_type == 'selected' and selected_ids:
            for customer_id in selected_ids:
                try:
                    customer = Customer.objects.get(id=customer_id)
                    recipients.append({
                        'type': 'customer',
                        'id': customer_id,
                        'context': {
                            'customer_name': customer.full_persian_name,
                        }
                    })
                except Customer.DoesNotExist:
                    continue
        
        elif target_type == 'all_customers':
            for customer in Customer.objects.filter(is_active=True):
                recipients.append({
                    'type': 'customer',
                    'id': customer.id,
                    'context': {
                        'customer_name': customer.full_persian_name,
                    }
                })
        
        elif target_type == 'vip_customers':
            for customer in Customer.objects.filter(is_vip=True, is_active=True):
                recipients.append({
                    'type': 'customer',
                    'id': customer.id,
                    'context': {
                        'customer_name': customer.full_persian_name,
                    }
                })
        
        if not recipients:
            return JsonResponse({
                'success': False,
                'error': _('No recipients found')
            })
        
        # Send bulk notifications
        system = PushNotificationSystem()
        stats = system.send_bulk_notifications(
            template_type=template_type,
            recipients=recipients,
            context_template=context_template,
            delivery_methods=delivery_methods
        )
        
        return JsonResponse({
            'success': True,
            'message': _('Bulk notifications sent successfully'),
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def schedule_notification_ajax(request):
    """Schedule notification for later delivery."""
    
    try:
        data = json.loads(request.body)
        
        template_type = data.get('template_type')
        recipient_type = data.get('recipient_type', 'customer')
        recipient_id = data.get('recipient_id')
        context = data.get('context', {})
        delivery_methods = data.get('delivery_methods', ['sms'])
        scheduled_datetime = data.get('scheduled_datetime')
        
        if not all([template_type, recipient_id, scheduled_datetime]):
            return JsonResponse({
                'success': False,
                'error': _('Missing required fields')
            })
        
        # Parse scheduled datetime
        scheduled_at = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
        
        # Create scheduled notification
        system = PushNotificationSystem()
        notifications = system.create_notification(
            template_type=template_type,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            context=context,
            delivery_methods=delivery_methods,
            scheduled_at=scheduled_at
        )
        
        return JsonResponse({
            'success': True,
            'message': _('Notification scheduled successfully'),
            'notifications_created': len(notifications),
            'scheduled_at': scheduled_at.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def template_preview_ajax(request, template_id):
    """Preview notification template with sample data."""
    
    try:
        template = get_object_or_404(NotificationTemplate, id=template_id)
        
        # Sample context data based on template type
        sample_context = {
            'customer_name': 'احمد محمدی',
            'contract_number': 'GI-2024-001',
            'amount': '5,000,000',
            'due_date': '1403/07/15',
            'remaining_weight': '2.5',
            'appointment_date': '1403/07/20',
            'appointment_time': '14:30',
            'offer_title': 'تخفیف ویژه طلا',
            'discount_percentage': '20',
            'expiry_date': '1403/08/01',
            'shop_name': 'طلا و جواهرات زرگر',
            'date': '1403/07/10',
        }
        
        # Render template with sample data
        rendered = template.render_content(sample_context)
        
        return JsonResponse({
            'success': True,
            'title': rendered['title'],
            'content': rendered['content'],
            'template_type': template.get_template_type_display(),
            'delivery_methods': template.delivery_methods,
            'available_variables': template.available_variables
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def notification_statistics_ajax(request):
    """Get notification statistics for dashboard."""
    
    try:
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        # Basic statistics
        stats = {
            'total_notifications': Notification.objects.count(),
            'pending_notifications': Notification.objects.filter(status='pending').count(),
            'sent_today': Notification.objects.filter(
                status='sent',
                sent_at__gte=today_start
            ).count(),
            'failed_today': Notification.objects.filter(
                status='failed',
                failed_at__gte=today_start
            ).count(),
            'delivered_today': Notification.objects.filter(
                status='delivered',
                delivered_at__gte=today_start
            ).count(),
        }
        
        # Weekly statistics
        weekly_stats = Notification.objects.filter(
            created_at__gte=week_start
        ).values('status').annotate(count=Count('id'))
        
        stats['weekly_breakdown'] = {item['status']: item['count'] for item in weekly_stats}
        
        # Monthly statistics by delivery method
        monthly_by_method = Notification.objects.filter(
            created_at__gte=month_start
        ).values('delivery_method').annotate(count=Count('id'))
        
        stats['monthly_by_method'] = {item['delivery_method']: item['count'] for item in monthly_by_method}
        
        # Template usage statistics
        template_usage = Notification.objects.filter(
            created_at__gte=month_start,
            template__isnull=False
        ).values('template__name', 'template__template_type').annotate(count=Count('id')).order_by('-count')[:10]
        
        stats['popular_templates'] = list(template_usage)
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def cancel_notification_ajax(request, notification_id):
    """Cancel a pending notification."""
    
    try:
        notification = get_object_or_404(Notification, id=notification_id)
        
        if notification.status not in ['pending', 'queued']:
            return JsonResponse({
                'success': False,
                'error': _('Cannot cancel notification in current status')
            })
        
        notification.cancel("Cancelled by user")
        
        return JsonResponse({
            'success': True,
            'message': _('Notification cancelled successfully')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def retry_notification_ajax(request, notification_id):
    """Retry a failed notification."""
    
    try:
        notification = get_object_or_404(Notification, id=notification_id)
        
        if not notification.can_retry:
            return JsonResponse({
                'success': False,
                'error': _('Cannot retry this notification')
            })
        
        # Reset notification for retry
        notification.status = 'pending'
        notification.scheduled_at = timezone.now()
        notification.error_message = ''
        notification.save(update_fields=['status', 'scheduled_at', 'error_message'])
        
        # Try to send immediately
        system = PushNotificationSystem()
        success = system.send_notification(notification)
        
        return JsonResponse({
            'success': success,
            'message': _('Notification retry initiated') if success else _('Retry failed')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })