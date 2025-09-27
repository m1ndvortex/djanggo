"""
Customer management views with loyalty and engagement features.
"""
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from zargar.core.mixins import TenantContextMixin
from .models import Customer, CustomerLoyaltyTransaction, CustomerNote
from .loyalty_models import (
    CustomerLoyaltyProgram,
    CustomerEngagementEvent,
    CustomerVIPTier,
    CustomerReferral,
    CustomerSpecialOffer
)
from .engagement_services import CustomerEngagementService, CustomerLoyaltyService


class CustomerLoyaltyDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Customer loyalty management dashboard with points tracking and tier management.
    """
    template_name = 'customers/loyalty_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get active loyalty program
        loyalty_service = CustomerLoyaltyService(self.request.tenant)
        loyalty_program = loyalty_service.get_active_loyalty_program()
        
        # Get loyalty statistics
        total_customers = Customer.objects.filter(tenant=self.request.tenant).count()
        vip_customers = Customer.objects.filter(tenant=self.request.tenant, is_vip=True).count()
        
        # Get tier distribution
        tier_distribution = CustomerVIPTier.objects.filter(
            customer__tenant=self.request.tenant,
            is_current=True
        ).values('tier').annotate(count=Count('id')).order_by('tier')
        
        # Get recent loyalty transactions
        recent_transactions = CustomerLoyaltyTransaction.objects.filter(
            customer__tenant=self.request.tenant
        ).select_related('customer').order_by('-created_at')[:10]
        
        # Get top customers by loyalty points
        top_customers = Customer.objects.filter(
            tenant=self.request.tenant,
            loyalty_points__gt=0
        ).order_by('-loyalty_points')[:10]
        
        # Calculate total points issued and redeemed
        points_stats = CustomerLoyaltyTransaction.objects.filter(
            customer__tenant=self.request.tenant
        ).aggregate(
            total_earned=Sum('points', filter=Q(points__gt=0)),
            total_redeemed=Sum('points', filter=Q(points__lt=0))
        )
        
        context.update({
            'loyalty_program': loyalty_program,
            'total_customers': total_customers,
            'vip_customers': vip_customers,
            'regular_customers': total_customers - vip_customers,
            'tier_distribution': list(tier_distribution),
            'recent_transactions': recent_transactions,
            'top_customers': top_customers,
            'points_stats': {
                'total_earned': points_stats['total_earned'] or 0,
                'total_redeemed': abs(points_stats['total_redeemed'] or 0),
                'net_points': (points_stats['total_earned'] or 0) + (points_stats['total_redeemed'] or 0)
            }
        })
        
        return context


class CustomerEngagementDashboardView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Customer engagement dashboard showing loyalty metrics and upcoming events.
    """
    template_name = 'customers/engagement_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get upcoming engagement events
        upcoming_events = CustomerEngagementEvent.objects.filter(
            customer__tenant=self.request.tenant,
            status='pending',
            scheduled_date__gte=timezone.now(),
            scheduled_date__lte=timezone.now() + timedelta(days=30)
        ).select_related('customer').order_by('scheduled_date')[:20]
        
        # Get recent engagement events
        recent_events = CustomerEngagementEvent.objects.filter(
            customer__tenant=self.request.tenant,
            status__in=['sent', 'delivered']
        ).select_related('customer').order_by('-sent_date')[:10]
        
        # Get engagement statistics
        engagement_stats = CustomerEngagementEvent.objects.filter(
            customer__tenant=self.request.tenant,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(
            total_events=Count('id'),
            sent_events=Count('id', filter=Q(status='sent')),
            delivered_events=Count('id', filter=Q(status='delivered')),
            failed_events=Count('id', filter=Q(status='failed'))
        )
        
        # Calculate engagement rate
        total_events = engagement_stats['total_events'] or 1
        engagement_rate = ((engagement_stats['delivered_events'] or 0) / total_events) * 100
        
        # Get event type distribution
        event_type_stats = CustomerEngagementEvent.objects.filter(
            customer__tenant=self.request.tenant,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values('event_type').annotate(count=Count('id')).order_by('-count')
        
        # Get customers with birthdays this month
        today = timezone.now().date()
        birthday_customers = Customer.objects.filter(
            tenant=self.request.tenant,
            is_active=True,
            birth_date__month=today.month
        ).order_by('birth_date__day')
        
        # Get customers with anniversaries this month
        anniversary_customers = Customer.objects.filter(
            tenant=self.request.tenant,
            is_active=True,
            created_at__month=today.month
        ).exclude(
            created_at__year=today.year
        ).order_by('created_at__day')
        
        context.update({
            'upcoming_events': upcoming_events,
            'recent_events': recent_events,
            'engagement_stats': engagement_stats,
            'engagement_rate': round(engagement_rate, 1),
            'event_type_stats': list(event_type_stats),
            'birthday_customers': birthday_customers,
            'anniversary_customers': anniversary_customers
        })
        
        return context


class BirthdayReminderView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    Birthday and anniversary reminder interface with gift suggestions and Persian templates.
    """
    template_name = 'customers/birthday_reminders.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        engagement_service = CustomerEngagementService(self.request.tenant)
        
        # Get customers with upcoming birthdays (next 30 days)
        upcoming_birthdays = []
        for days_ahead in range(1, 31):
            try:
                events = engagement_service.create_birthday_reminders(days_ahead=days_ahead)
                for event in events:
                    upcoming_birthdays.append({
                        'customer': event.customer,
                        'days_ahead': days_ahead,
                        'event': event,
                        'gift_suggestions': event.suggested_gifts
                    })
            except Exception:
                continue
        
        # Get customers with upcoming anniversaries (next 30 days)
        upcoming_anniversaries = []
        for days_ahead in range(1, 31):
            try:
                events = engagement_service.create_anniversary_reminders(days_ahead=days_ahead)
                for event in events:
                    years_as_customer = timezone.now().year - event.customer.created_at.year
                    upcoming_anniversaries.append({
                        'customer': event.customer,
                        'days_ahead': days_ahead,
                        'years_as_customer': years_as_customer,
                        'event': event,
                        'gift_suggestions': event.suggested_gifts
                    })
            except Exception:
                continue
        
        # Get Persian cultural events
        cultural_events = [
            {
                'type': 'nowruz',
                'name': 'نوروز',
                'description': 'سال نو فارسی',
                'eligible_customers': Customer.objects.filter(
                    tenant=self.request.tenant,
                    is_vip=True,
                    is_active=True
                ).count()
            },
            {
                'type': 'yalda',
                'name': 'شب یلدا',
                'description': 'طولانی‌ترین شب سال',
                'eligible_customers': Customer.objects.filter(
                    tenant=self.request.tenant,
                    is_vip=True,
                    is_active=True
                ).count()
            },
            {
                'type': 'mehregan',
                'name': 'مهرگان',
                'description': 'جشن مهر و دوستی',
                'eligible_customers': Customer.objects.filter(
                    tenant=self.request.tenant,
                    is_vip=True,
                    is_active=True
                ).count()
            }
        ]
        
        # Get recent birthday/anniversary events
        recent_events = CustomerEngagementEvent.objects.filter(
            customer__tenant=self.request.tenant,
            event_type__in=['birthday', 'anniversary'],
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('customer').order_by('-created_at')[:10]
        
        context.update({
            'upcoming_birthdays': upcoming_birthdays[:10],
            'upcoming_anniversaries': upcoming_anniversaries[:10],
            'cultural_events': cultural_events,
            'recent_events': recent_events
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle creating birthday/anniversary reminders."""
        action = request.POST.get('action')
        engagement_service = CustomerEngagementService(request.tenant)
        
        if action == 'create_birthday_reminders':
            days_ahead = int(request.POST.get('days_ahead', 7))
            events = engagement_service.create_birthday_reminders(days_ahead=days_ahead)
            messages.success(request, f'{len(events)} یادآوری تولد ایجاد شد.')
            
        elif action == 'create_anniversary_reminders':
            days_ahead = int(request.POST.get('days_ahead', 7))
            events = engagement_service.create_anniversary_reminders(days_ahead=days_ahead)
            messages.success(request, f'{len(events)} یادآوری سالگرد ایجاد شد.')
            
        elif action == 'create_cultural_event':
            event_type = request.POST.get('event_type')
            events = engagement_service.create_cultural_event_reminders(event_type)
            messages.success(request, f'{len(events)} یادآوری {event_type} ایجاد شد.')
        
        return redirect('customers:birthday_reminders')


class CustomerLoyaltyDetailView(LoginRequiredMixin, TenantContextMixin, DetailView):
    """
    Detailed view of customer loyalty information.
    """
    model = Customer
    template_name = 'customers/loyalty_detail.html'
    context_object_name = 'customer'
    
    def get_queryset(self):
        return Customer.objects.filter(tenant=self.request.tenant)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        # Get customer's VIP tier history
        vip_tiers = CustomerVIPTier.objects.filter(
            customer=customer
        ).order_by('-effective_date')
        
        # Get current VIP tier
        current_tier = vip_tiers.filter(is_current=True).first()
        
        # Get loyalty transactions
        loyalty_transactions = CustomerLoyaltyTransaction.objects.filter(
            customer=customer
        ).order_by('-created_at')[:20]
        
        # Get engagement events
        engagement_events = CustomerEngagementEvent.objects.filter(
            customer=customer
        ).order_by('-scheduled_date')[:10]
        
        # Get special offers
        special_offers = CustomerSpecialOffer.objects.filter(
            customer=customer
        ).order_by('-created_at')[:10]
        
        # Get referrals made by customer
        referrals_made = CustomerReferral.objects.filter(
            referrer=customer
        ).select_related('referred_customer').order_by('-referral_date')
        
        # Calculate loyalty statistics
        loyalty_stats = CustomerLoyaltyTransaction.objects.filter(
            customer=customer
        ).aggregate(
            total_earned=Sum('points', filter=Q(points__gt=0)),
            total_redeemed=Sum('points', filter=Q(points__lt=0)),
            transaction_count=Count('id')
        )
        
        context.update({
            'vip_tiers': vip_tiers,
            'current_tier': current_tier,
            'loyalty_transactions': loyalty_transactions,
            'engagement_events': engagement_events,
            'special_offers': special_offers,
            'referrals_made': referrals_made,
            'loyalty_stats': {
                'total_earned': loyalty_stats['total_earned'] or 0,
                'total_redeemed': abs(loyalty_stats['total_redeemed'] or 0),
                'transaction_count': loyalty_stats['transaction_count'] or 0
            }
        })
        
        return context


class CustomerEngagementEventListView(LoginRequiredMixin, TenantContextMixin, ListView):
    """
    List view for customer engagement events.
    """
    model = CustomerEngagementEvent
    template_name = 'customers/engagement_events.html'
    context_object_name = 'events'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CustomerEngagementEvent.objects.filter(
            customer__tenant=self.request.tenant
        ).select_related('customer').order_by('-scheduled_date')
        
        # Filter by event type
        event_type = self.request.GET.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by customer
        customer_id = self.request.GET.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        context['event_types'] = CustomerEngagementEvent.EVENT_TYPES
        context['status_choices'] = CustomerEngagementEvent.STATUS_CHOICES
        context['customers'] = Customer.objects.filter(
            tenant=self.request.tenant,
            is_active=True
        ).order_by('persian_first_name', 'first_name')
        
        # Get current filters
        context['current_filters'] = {
            'event_type': self.request.GET.get('event_type', ''),
            'status': self.request.GET.get('status', ''),
            'customer': self.request.GET.get('customer', '')
        }
        
        return context


# AJAX Views for dynamic functionality
class CustomerLoyaltyAjaxView(LoginRequiredMixin, TenantContextMixin, TemplateView):
    """
    AJAX endpoints for customer loyalty operations.
    """
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'award_points':
            return self.award_points(request)
        elif action == 'redeem_points':
            return self.redeem_points(request)
        elif action == 'update_tier':
            return self.update_tier(request)
        elif action == 'create_special_offer':
            return self.create_special_offer(request)
        
        return JsonResponse({'success': False, 'error': 'Invalid action'})
    
    def award_points(self, request):
        """Award loyalty points to a customer."""
        try:
            customer_id = request.POST.get('customer_id')
            points = int(request.POST.get('points', 0))
            reason = request.POST.get('reason', '')
            
            customer = get_object_or_404(Customer, id=customer_id, tenant=request.tenant)
            customer.add_loyalty_points(points, reason)
            
            return JsonResponse({
                'success': True,
                'message': f'{points} امتیاز به {customer.full_persian_name} اعطا شد.',
                'new_balance': customer.loyalty_points
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def redeem_points(self, request):
        """Redeem loyalty points for a customer."""
        try:
            customer_id = request.POST.get('customer_id')
            points = int(request.POST.get('points', 0))
            reason = request.POST.get('reason', '')
            
            customer = get_object_or_404(Customer, id=customer_id, tenant=request.tenant)
            
            if customer.redeem_loyalty_points(points, reason):
                return JsonResponse({
                    'success': True,
                    'message': f'{points} امتیاز از {customer.full_persian_name} کسر شد.',
                    'new_balance': customer.loyalty_points
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'موجودی امتیاز کافی نیست.'
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def update_tier(self, request):
        """Update customer VIP tier."""
        try:
            customer_id = request.POST.get('customer_id')
            customer = get_object_or_404(Customer, id=customer_id, tenant=request.tenant)
            
            loyalty_service = CustomerLoyaltyService(request.tenant)
            tier_record = loyalty_service.update_customer_tier(customer)
            
            if tier_record:
                return JsonResponse({
                    'success': True,
                    'message': f'{customer.full_persian_name} به سطح {tier_record.get_tier_display()} ارتقاء یافت.',
                    'new_tier': tier_record.tier
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'مشتری برای ارتقاء سطح واجد شرایط نیست.'
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def create_special_offer(self, request):
        """Create a special offer for a customer."""
        try:
            customer_id = request.POST.get('customer_id')
            offer_type = request.POST.get('offer_type')
            discount_percentage = request.POST.get('discount_percentage', 0)
            valid_days = request.POST.get('valid_days', 7)
            
            customer = get_object_or_404(Customer, id=customer_id, tenant=request.tenant)
            loyalty_service = CustomerLoyaltyService(request.tenant)
            
            offer = loyalty_service.create_special_offer(
                customer,
                offer_type,
                discount_percentage=float(discount_percentage),
                valid_days=int(valid_days)
            )
            
            return JsonResponse({
                'success': True,
                'message': f'پیشنهاد ویژه برای {customer.full_persian_name} ایجاد شد.',
                'offer_id': offer.id
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class PlaceholderView(TemplateView):
    """
    Placeholder view for customers module.
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'module': 'customers',
            'status': 'placeholder',
            'message': 'Customers module will be implemented in later tasks'
        })