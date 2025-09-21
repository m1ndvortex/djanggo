"""
Celery tasks for customer loyalty and engagement system.
"""
from celery import shared_task
from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context
from .engagement_services import CustomerEngagementService, CustomerLoyaltyService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_daily_engagement_events(self):
    """
    Daily task to process customer engagement events.
    Creates birthday and anniversary reminders, sends pending events.
    """
    try:
        Tenant = get_tenant_model()
        active_tenants = Tenant.objects.filter(is_active=True)
        
        total_created = 0
        total_sent = 0
        total_failed = 0
        
        for tenant in active_tenants:
            try:
                with tenant_context(tenant):
                    engagement_service = CustomerEngagementService(tenant)
                    
                    # Create birthday reminders (7 days ahead)
                    birthday_events = engagement_service.create_birthday_reminders(days_ahead=7)
                    total_created += len(birthday_events)
                    
                    # Create anniversary reminders (7 days ahead)
                    anniversary_events = engagement_service.create_anniversary_reminders(days_ahead=7)
                    total_created += len(anniversary_events)
                    
                    # Send pending events
                    send_results = engagement_service.send_pending_events()
                    total_sent += send_results['sent']
                    total_failed += send_results['failed']
                    
                    logger.info(
                        f"Processed engagement for tenant {tenant.name}: "
                        f"Created {len(birthday_events + anniversary_events)} events, "
                        f"Sent {send_results['sent']} events"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing engagement for tenant {tenant.id}: {e}")
                continue
        
        logger.info(
            f"Daily engagement processing completed: "
            f"Created {total_created} events, "
            f"Sent {total_sent} events, "
            f"Failed {total_failed} events"
        )
        
        return {
            'status': 'success',
            'created_events': total_created,
            'sent_events': total_sent,
            'failed_events': total_failed
        }
        
    except Exception as exc:
        logger.error(f"Daily engagement processing failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * 5)  # Retry in 5 minutes


@shared_task(bind=True, max_retries=3)
def process_cultural_events(self, event_type):
    """
    Task to process cultural events (Nowruz, Yalda, Mehregan).
    
    Args:
        event_type: Type of cultural event ('nowruz', 'yalda', 'mehregan')
    """
    try:
        Tenant = get_tenant_model()
        active_tenants = Tenant.objects.filter(is_active=True)
        
        total_created = 0
        
        for tenant in active_tenants:
            try:
                with tenant_context(tenant):
                    engagement_service = CustomerEngagementService(tenant)
                    
                    # Create cultural event reminders
                    cultural_events = engagement_service.create_cultural_event_reminders(event_type)
                    total_created += len(cultural_events)
                    
                    logger.info(
                        f"Created {len(cultural_events)} {event_type} events for tenant {tenant.name}"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing {event_type} for tenant {tenant.id}: {e}")
                continue
        
        logger.info(f"Cultural event processing completed: Created {total_created} {event_type} events")
        
        return {
            'status': 'success',
            'event_type': event_type,
            'created_events': total_created
        }
        
    except Exception as exc:
        logger.error(f"Cultural event processing failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * 5)


@shared_task(bind=True, max_retries=3)
def update_customer_loyalty_tiers(self):
    """
    Weekly task to update customer loyalty tiers based on recent purchases.
    """
    try:
        from datetime import timedelta
        
        Tenant = get_tenant_model()
        active_tenants = Tenant.objects.filter(is_active=True)
        
        total_upgrades = 0
        
        for tenant in active_tenants:
            try:
                with tenant_context(tenant):
                    from .models import Customer
                    
                    loyalty_service = CustomerLoyaltyService(tenant)
                    
                    # Get customers with recent purchases (last 30 days)
                    recent_date = timezone.now() - timedelta(days=30)
                    customers_to_check = Customer.objects.filter(
                        is_active=True,
                        last_purchase_date__gte=recent_date
                    )
                    
                    upgrades_count = 0
                    
                    for customer in customers_to_check:
                        try:
                            tier_upgrade = loyalty_service.update_customer_tier(customer)
                            if tier_upgrade:
                                upgrades_count += 1
                                logger.info(
                                    f"Upgraded customer {customer.full_persian_name} "
                                    f"to {tier_upgrade.tier} tier"
                                )
                        except Exception as e:
                            logger.error(f"Error updating tier for customer {customer.id}: {e}")
                            continue
                    
                    total_upgrades += upgrades_count
                    
                    logger.info(
                        f"Processed loyalty tiers for tenant {tenant.name}: "
                        f"{upgrades_count} upgrades from {customers_to_check.count()} customers"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing loyalty tiers for tenant {tenant.id}: {e}")
                continue
        
        logger.info(f"Loyalty tier processing completed: {total_upgrades} total upgrades")
        
        return {
            'status': 'success',
            'total_upgrades': total_upgrades
        }
        
    except Exception as exc:
        logger.error(f"Loyalty tier processing failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * 10)  # Retry in 10 minutes


@shared_task(bind=True, max_retries=3)
def send_pending_engagement_events(self):
    """
    Hourly task to send pending engagement events that are due.
    """
    try:
        Tenant = get_tenant_model()
        active_tenants = Tenant.objects.filter(is_active=True)
        
        total_sent = 0
        total_failed = 0
        
        for tenant in active_tenants:
            try:
                with tenant_context(tenant):
                    engagement_service = CustomerEngagementService(tenant)
                    
                    # Send pending events
                    results = engagement_service.send_pending_events()
                    total_sent += results['sent']
                    total_failed += results['failed']
                    
                    if results['sent'] > 0 or results['failed'] > 0:
                        logger.info(
                            f"Sent engagement events for tenant {tenant.name}: "
                            f"Sent {results['sent']}, Failed {results['failed']}"
                        )
                    
            except Exception as e:
                logger.error(f"Error sending events for tenant {tenant.id}: {e}")
                continue
        
        if total_sent > 0 or total_failed > 0:
            logger.info(
                f"Engagement event sending completed: "
                f"Sent {total_sent} events, Failed {total_failed} events"
            )
        
        return {
            'status': 'success',
            'sent_events': total_sent,
            'failed_events': total_failed
        }
        
    except Exception as exc:
        logger.error(f"Engagement event sending failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * 2)  # Retry in 2 minutes


@shared_task(bind=True, max_retries=3)
def expire_old_loyalty_points(self):
    """
    Monthly task to expire old loyalty points based on program settings.
    """
    try:
        from datetime import timedelta
        from .loyalty_models import CustomerLoyaltyProgram
        
        Tenant = get_tenant_model()
        active_tenants = Tenant.objects.filter(is_active=True)
        
        total_expired_points = 0
        total_customers_affected = 0
        
        for tenant in active_tenants:
            try:
                with tenant_context(tenant):
                    from .models import Customer, CustomerLoyaltyTransaction
                    
                    # Get active loyalty program
                    loyalty_program = CustomerLoyaltyProgram.objects.filter(
                        is_active=True
                    ).first()
                    
                    if not loyalty_program:
                        continue
                    
                    # Calculate expiration date
                    expiration_date = timezone.now() - timedelta(
                        days=loyalty_program.points_expire_months * 30
                    )
                    
                    # Find customers with old points
                    customers_with_old_points = Customer.objects.filter(
                        is_active=True,
                        loyalty_points__gt=0,
                        loyalty_transactions__created_at__lt=expiration_date,
                        loyalty_transactions__transaction_type='earned'
                    ).distinct()
                    
                    expired_points = 0
                    customers_affected = 0
                    
                    for customer in customers_with_old_points:
                        # Calculate expired points for this customer
                        old_transactions = CustomerLoyaltyTransaction.objects.filter(
                            customer=customer,
                            transaction_type='earned',
                            created_at__lt=expiration_date
                        )
                        
                        points_to_expire = sum(
                            transaction.points for transaction in old_transactions
                            if transaction.points > 0
                        )
                        
                        if points_to_expire > 0:
                            # Don't expire more points than customer has
                            points_to_expire = min(points_to_expire, customer.loyalty_points)
                            
                            if points_to_expire > 0:
                                # Expire the points
                                customer.loyalty_points -= points_to_expire
                                customer.save(update_fields=['loyalty_points', 'updated_at'])
                                
                                # Create expiration transaction
                                CustomerLoyaltyTransaction.objects.create(
                                    customer=customer,
                                    points=-points_to_expire,
                                    transaction_type='expired',
                                    reason=f"Points expired after {loyalty_program.points_expire_months} months"
                                )
                                
                                expired_points += points_to_expire
                                customers_affected += 1
                                
                                logger.info(
                                    f"Expired {points_to_expire} points for customer "
                                    f"{customer.full_persian_name}"
                                )
                    
                    total_expired_points += expired_points
                    total_customers_affected += customers_affected
                    
                    if expired_points > 0:
                        logger.info(
                            f"Expired loyalty points for tenant {tenant.name}: "
                            f"{expired_points} points from {customers_affected} customers"
                        )
                    
            except Exception as e:
                logger.error(f"Error expiring points for tenant {tenant.id}: {e}")
                continue
        
        if total_expired_points > 0:
            logger.info(
                f"Loyalty points expiration completed: "
                f"Expired {total_expired_points} points from {total_customers_affected} customers"
            )
        
        return {
            'status': 'success',
            'expired_points': total_expired_points,
            'customers_affected': total_customers_affected
        }
        
    except Exception as exc:
        logger.error(f"Loyalty points expiration failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * 15)  # Retry in 15 minutes


@shared_task(bind=True, max_retries=3)
def create_birthday_special_offers(self):
    """
    Daily task to create special birthday offers for customers.
    """
    try:
        from datetime import timedelta
        import jdatetime
        
        Tenant = get_tenant_model()
        active_tenants = Tenant.objects.filter(is_active=True)
        
        total_offers_created = 0
        
        # Get tomorrow's date in Shamsi calendar
        tomorrow_shamsi = jdatetime.date.today() + jdatetime.timedelta(days=1)
        
        for tenant in active_tenants:
            try:
                with tenant_context(tenant):
                    from .models import Customer
                    
                    loyalty_service = CustomerLoyaltyService(tenant)
                    
                    # Find customers with birthdays tomorrow
                    customers_with_birthdays = Customer.objects.filter(
                        is_active=True,
                        birth_date_shamsi__isnull=False
                    )
                    
                    offers_created = 0
                    
                    for customer in customers_with_birthdays:
                        try:
                            # Parse Shamsi birth date
                            birth_parts = customer.birth_date_shamsi.split('/')
                            if len(birth_parts) != 3:
                                continue
                            
                            birth_month = int(birth_parts[1])
                            birth_day = int(birth_parts[2])
                            
                            # Check if birthday matches tomorrow
                            if (birth_month == tomorrow_shamsi.month and 
                                birth_day == tomorrow_shamsi.day):
                                
                                # Create birthday special offer
                                offer = loyalty_service.create_special_offer(
                                    customer,
                                    'birthday_discount',
                                    discount_percentage=15,
                                    valid_days=7,
                                    minimum_purchase=500000  # 500K Toman minimum
                                )
                                
                                offers_created += 1
                                
                                logger.info(
                                    f"Created birthday offer for {customer.full_persian_name}"
                                )
                                
                        except (ValueError, IndexError) as e:
                            logger.warning(
                                f"Invalid birth date format for customer {customer.id}: {e}"
                            )
                            continue
                    
                    total_offers_created += offers_created
                    
                    if offers_created > 0:
                        logger.info(
                            f"Created birthday offers for tenant {tenant.name}: "
                            f"{offers_created} offers"
                        )
                    
            except Exception as e:
                logger.error(f"Error creating birthday offers for tenant {tenant.id}: {e}")
                continue
        
        if total_offers_created > 0:
            logger.info(
                f"Birthday offer creation completed: {total_offers_created} total offers created"
            )
        
        return {
            'status': 'success',
            'offers_created': total_offers_created
        }
        
    except Exception as exc:
        logger.error(f"Birthday offer creation failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * 5)  # Retry in 5 minutes