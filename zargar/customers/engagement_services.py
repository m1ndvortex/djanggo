"""
Customer engagement and loyalty services for zargar project.
"""
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.template.loader import render_to_string
from django.conf import settings
from typing import List, Dict, Optional
import jdatetime
from datetime import datetime, timedelta
import logging

from .models import Customer
from .loyalty_models import (
    CustomerLoyaltyProgram,
    CustomerEngagementEvent,
    CustomerVIPTier,
    CustomerReferral,
    CustomerSpecialOffer
)

logger = logging.getLogger(__name__)


class CustomerEngagementService:
    """
    Service for managing customer engagement events and reminders.
    """
    
    def __init__(self, tenant):
        self.tenant = tenant
    
    def create_birthday_reminders(self, days_ahead: int = 7) -> List[CustomerEngagementEvent]:
        """
        Create birthday reminder events for customers whose birthdays are coming up.
        
        Args:
            days_ahead: Number of days ahead to create reminders
            
        Returns:
            List of created engagement events
        """
        created_events = []
        
        # Get current Shamsi date
        today_shamsi = jdatetime.date.today()
        target_date_shamsi = today_shamsi + jdatetime.timedelta(days=days_ahead)
        
        # Find customers with birthdays on target date
        customers_with_birthdays = Customer.objects.filter(
            tenant=self.tenant,
            is_active=True,
            birth_date_shamsi__isnull=False
        )
        
        for customer in customers_with_birthdays:
            try:
                # Parse Shamsi birth date
                birth_parts = customer.birth_date_shamsi.split('/')
                if len(birth_parts) != 3:
                    continue
                
                birth_month = int(birth_parts[1])
                birth_day = int(birth_parts[2])
                
                # Check if birthday matches target date
                if (birth_month == target_date_shamsi.month and 
                    birth_day == target_date_shamsi.day):
                    
                    # Check if reminder already exists
                    existing_reminder = CustomerEngagementEvent.objects.filter(
                        customer=customer,
                        event_type='birthday',
                        scheduled_date__date=target_date_shamsi.togregorian(),
                        status__in=['pending', 'sent']
                    ).exists()
                    
                    if not existing_reminder:
                        # Generate personalized gift suggestions
                        gift_suggestions = self._generate_gift_suggestions(customer)
                        
                        # Create birthday reminder event
                        event = CustomerEngagementEvent.objects.create(
                            customer=customer,
                            event_type='birthday',
                            title=f"Birthday Reminder - {customer.full_persian_name}",
                            title_persian=f"یادآوری تولد - {customer.full_persian_name}",
                            message=self._generate_birthday_message(customer),
                            message_persian=self._generate_birthday_message_persian(customer),
                            scheduled_date=timezone.make_aware(
                                datetime.combine(target_date_shamsi.togregorian(), datetime.min.time())
                            ),
                            delivery_method='sms',
                            suggested_gifts=gift_suggestions,
                            bonus_points_awarded=self._get_birthday_bonus_points()
                        )
                        
                        created_events.append(event)
                        logger.info(f"Created birthday reminder for {customer.full_persian_name}")
                        
            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid birth date format for customer {customer.id}: {e}")
                continue
        
        return created_events
    
    def create_anniversary_reminders(self, days_ahead: int = 7) -> List[CustomerEngagementEvent]:
        """
        Create anniversary reminder events for customers.
        
        Args:
            days_ahead: Number of days ahead to create reminders
            
        Returns:
            List of created engagement events
        """
        created_events = []
        
        # Calculate target date
        target_date = timezone.now().date() + timedelta(days=days_ahead)
        
        # Find customers with purchase anniversaries
        customers_with_anniversaries = Customer.objects.filter(
            tenant=self.tenant,
            is_active=True,
            created_at__month=target_date.month,
            created_at__day=target_date.day
        ).exclude(
            created_at__year=target_date.year  # Exclude customers created this year
        )
        
        for customer in customers_with_anniversaries:
            # Calculate years as customer
            years_as_customer = target_date.year - customer.created_at.year
            
            # Check if reminder already exists
            existing_reminder = CustomerEngagementEvent.objects.filter(
                customer=customer,
                event_type='anniversary',
                scheduled_date__date=target_date,
                status__in=['pending', 'sent']
            ).exists()
            
            if not existing_reminder:
                # Generate personalized gift suggestions
                gift_suggestions = self._generate_gift_suggestions(customer, occasion='anniversary')
                
                # Create anniversary reminder event
                event = CustomerEngagementEvent.objects.create(
                    customer=customer,
                    event_type='anniversary',
                    title=f"Anniversary Reminder - {customer.full_persian_name} ({years_as_customer} years)",
                    title_persian=f"یادآوری سالگرد - {customer.full_persian_name} ({years_as_customer} سال)",
                    message=self._generate_anniversary_message(customer, years_as_customer),
                    message_persian=self._generate_anniversary_message_persian(customer, years_as_customer),
                    scheduled_date=timezone.make_aware(
                        datetime.combine(target_date, datetime.min.time())
                    ),
                    delivery_method='sms',
                    suggested_gifts=gift_suggestions,
                    bonus_points_awarded=self._get_anniversary_bonus_points()
                )
                
                created_events.append(event)
                logger.info(f"Created anniversary reminder for {customer.full_persian_name}")
        
        return created_events
    
    def create_cultural_event_reminders(self, event_type: str) -> List[CustomerEngagementEvent]:
        """
        Create reminders for Persian cultural events (Nowruz, Yalda, etc.).
        
        Args:
            event_type: Type of cultural event ('nowruz', 'yalda', 'mehregan')
            
        Returns:
            List of created engagement events
        """
        created_events = []
        
        # Get active VIP customers for cultural events
        vip_customers = Customer.objects.filter(
            tenant=self.tenant,
            is_active=True,
            is_vip=True
        )
        
        # Cultural event dates (approximate - should be updated annually)
        cultural_dates = {
            'nowruz': jdatetime.date(jdatetime.date.today().year, 1, 1),  # 1st of Farvardin
            'yalda': jdatetime.date(jdatetime.date.today().year, 10, 1),  # 1st of Dey (approximate)
            'mehregan': jdatetime.date(jdatetime.date.today().year, 7, 16),  # 16th of Mehr
        }
        
        if event_type not in cultural_dates:
            logger.warning(f"Unknown cultural event type: {event_type}")
            return created_events
        
        event_date = cultural_dates[event_type]
        
        for customer in vip_customers:
            # Check if reminder already exists
            existing_reminder = CustomerEngagementEvent.objects.filter(
                customer=customer,
                event_type=event_type,
                scheduled_date__date=event_date.togregorian(),
                status__in=['pending', 'sent']
            ).exists()
            
            if not existing_reminder:
                # Create cultural event reminder
                event = CustomerEngagementEvent.objects.create(
                    customer=customer,
                    event_type=event_type,
                    title=f"{event_type.title()} Greeting - {customer.full_persian_name}",
                    title_persian=self._get_cultural_event_title_persian(event_type, customer),
                    message=self._generate_cultural_event_message(event_type, customer),
                    message_persian=self._generate_cultural_event_message_persian(event_type, customer),
                    scheduled_date=timezone.make_aware(
                        datetime.combine(event_date.togregorian(), datetime.min.time())
                    ),
                    delivery_method='sms',
                    bonus_points_awarded=self._get_cultural_event_bonus_points(event_type)
                )
                
                created_events.append(event)
                logger.info(f"Created {event_type} reminder for {customer.full_persian_name}")
        
        return created_events
    
    def send_pending_events(self) -> Dict[str, int]:
        """
        Send all pending engagement events that are due.
        
        Returns:
            Dictionary with counts of sent, failed, and skipped events
        """
        results = {'sent': 0, 'failed': 0, 'skipped': 0}
        
        # Get pending events that are due
        now = timezone.now()
        pending_events = CustomerEngagementEvent.objects.filter(
            customer__tenant=self.tenant,
            status='pending',
            scheduled_date__lte=now
        ).select_related('customer')
        
        for event in pending_events:
            try:
                success = self._send_engagement_event(event)
                if success:
                    event.mark_as_sent()
                    
                    # Award bonus points if applicable
                    if event.bonus_points_awarded > 0:
                        event.customer.add_loyalty_points(
                            event.bonus_points_awarded,
                            f"{event.get_event_type_display()} bonus"
                        )
                    
                    results['sent'] += 1
                    logger.info(f"Sent engagement event {event.id} to {event.customer.full_persian_name}")
                else:
                    event.mark_as_failed("Failed to send message")
                    results['failed'] += 1
                    logger.error(f"Failed to send engagement event {event.id}")
                    
            except Exception as e:
                event.mark_as_failed(str(e))
                results['failed'] += 1
                logger.error(f"Error sending engagement event {event.id}: {e}")
        
        return results
    
    def _generate_gift_suggestions(self, customer: Customer, occasion: str = 'birthday') -> List[Dict]:
        """
        Generate personalized gift suggestions based on customer history and preferences.
        """
        suggestions = []
        
        # Base suggestions by occasion
        if occasion == 'birthday':
            base_suggestions = [
                {'type': 'ring', 'name_persian': 'انگشتر طلا', 'price_range': '5000000-15000000'},
                {'type': 'necklace', 'name_persian': 'گردنبند طلا', 'price_range': '8000000-25000000'},
                {'type': 'earrings', 'name_persian': 'گوشواره طلا', 'price_range': '3000000-12000000'},
                {'type': 'bracelet', 'name_persian': 'دستبند طلا', 'price_range': '4000000-18000000'},
            ]
        elif occasion == 'anniversary':
            base_suggestions = [
                {'type': 'jewelry_set', 'name_persian': 'سرویس طلا', 'price_range': '15000000-50000000'},
                {'type': 'watch', 'name_persian': 'ساعت طلا', 'price_range': '20000000-80000000'},
                {'type': 'pendant', 'name_persian': 'آویز طلا', 'price_range': '6000000-20000000'},
            ]
        else:
            base_suggestions = [
                {'type': 'charm', 'name_persian': 'پلاک طلا', 'price_range': '2000000-8000000'},
                {'type': 'coin', 'name_persian': 'سکه طلا', 'price_range': '10000000-30000000'},
            ]
        
        # Customize based on customer's VIP tier and purchase history
        if customer.is_vip:
            # Add premium suggestions for VIP customers
            premium_suggestions = [
                {'type': 'diamond_ring', 'name_persian': 'انگشتر الماس', 'price_range': '25000000-100000000'},
                {'type': 'emerald_necklace', 'name_persian': 'گردنبند زمرد', 'price_range': '30000000-120000000'},
            ]
            suggestions.extend(premium_suggestions)
        
        suggestions.extend(base_suggestions)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _generate_birthday_message(self, customer: Customer) -> str:
        """Generate English birthday message."""
        return f"Happy Birthday {customer.full_name}! We hope your special day is filled with joy and happiness. Visit us for exclusive birthday offers!"
    
    def _generate_birthday_message_persian(self, customer: Customer) -> str:
        """Generate Persian birthday message."""
        return f"تولدت مبارک {customer.full_persian_name} عزیز! امیدواریم روز ویژه‌ات پر از شادی و خوشحالی باشه. برای پیشنهادات ویژه تولد به ما سر بزن!"
    
    def _generate_anniversary_message(self, customer: Customer, years: int) -> str:
        """Generate English anniversary message."""
        return f"Congratulations {customer.full_name}! You've been our valued customer for {years} years. Thank you for your loyalty!"
    
    def _generate_anniversary_message_persian(self, customer: Customer, years: int) -> str:
        """Generate Persian anniversary message."""
        return f"تبریک {customer.full_persian_name} عزیز! {years} سال است که مشتری ارزشمند ما هستید. از وفاداری شما متشکریم!"
    
    def _generate_cultural_event_message(self, event_type: str, customer: Customer) -> str:
        """Generate English cultural event message."""
        messages = {
            'nowruz': f"Happy Nowruz {customer.full_name}! Wishing you a prosperous new year filled with joy and success!",
            'yalda': f"Happy Yalda Night {customer.full_name}! May this longest night bring you warmth and happiness!",
            'mehregan': f"Happy Mehregan {customer.full_name}! Celebrating the beauty of autumn and friendship with you!"
        }
        return messages.get(event_type, f"Happy {event_type} {customer.full_name}!")
    
    def _generate_cultural_event_message_persian(self, event_type: str, customer: Customer) -> str:
        """Generate Persian cultural event message."""
        messages = {
            'nowruz': f"نوروز مبارک {customer.full_persian_name} عزیز! سال نو برایتان پر از شادی و موفقیت باشد!",
            'yalda': f"شب یلدا مبارک {customer.full_persian_name} عزیز! این طولانی‌ترین شب برایتان گرمی و خوشحالی به ارمغان بیاورد!",
            'mehregan': f"مهرگان مبارک {customer.full_persian_name} عزیز! زیبایی پاییز و دوستی را با شما جشن می‌گیریم!"
        }
        return messages.get(event_type, f"{event_type} مبارک {customer.full_persian_name} عزیز!")
    
    def _get_cultural_event_title_persian(self, event_type: str, customer: Customer) -> str:
        """Get Persian title for cultural events."""
        titles = {
            'nowruz': f"تبریک نوروز - {customer.full_persian_name}",
            'yalda': f"تبریک شب یلدا - {customer.full_persian_name}",
            'mehregan': f"تبریک مهرگان - {customer.full_persian_name}"
        }
        return titles.get(event_type, f"تبریک {event_type} - {customer.full_persian_name}")
    
    def _get_birthday_bonus_points(self) -> int:
        """Get birthday bonus points from active loyalty program."""
        program = CustomerLoyaltyProgram.objects.filter(
            tenant=self.tenant,
            is_active=True
        ).first()
        return program.birthday_bonus_points if program else 1000
    
    def _get_anniversary_bonus_points(self) -> int:
        """Get anniversary bonus points from active loyalty program."""
        program = CustomerLoyaltyProgram.objects.filter(
            tenant=self.tenant,
            is_active=True
        ).first()
        return program.anniversary_bonus_points if program else 500
    
    def _get_cultural_event_bonus_points(self, event_type: str) -> int:
        """Get cultural event bonus points from active loyalty program."""
        program = CustomerLoyaltyProgram.objects.filter(
            tenant=self.tenant,
            is_active=True
        ).first()
        
        if not program:
            return 500
        
        bonus_mapping = {
            'nowruz': program.nowruz_bonus_points,
            'yalda': program.yalda_bonus_points,
            'mehregan': 1000,  # Default for Mehregan
        }
        return bonus_mapping.get(event_type, 500)
    
    def _send_engagement_event(self, event: CustomerEngagementEvent) -> bool:
        """
        Send engagement event via specified delivery method.
        
        This is a placeholder - actual implementation would integrate with
        SMS/Email services like Kavenegar, Melipayamak, etc.
        """
        try:
            if event.delivery_method == 'sms':
                return self._send_sms(event)
            elif event.delivery_method == 'email':
                return self._send_email(event)
            elif event.delivery_method == 'whatsapp':
                return self._send_whatsapp(event)
            else:
                logger.warning(f"Unsupported delivery method: {event.delivery_method}")
                return False
        except Exception as e:
            logger.error(f"Error sending engagement event: {e}")
            return False
    
    def _send_sms(self, event: CustomerEngagementEvent) -> bool:
        """Send SMS message (placeholder for actual SMS service integration)."""
        # TODO: Integrate with Iranian SMS services like Kavenegar, Melipayamak
        logger.info(f"SMS sent to {event.customer.phone_number}: {event.message_persian}")
        return True
    
    def _send_email(self, event: CustomerEngagementEvent) -> bool:
        """Send email message (placeholder for actual email service integration)."""
        # TODO: Integrate with email service
        logger.info(f"Email sent to {event.customer.email}: {event.title_persian}")
        return True
    
    def _send_whatsapp(self, event: CustomerEngagementEvent) -> bool:
        """Send WhatsApp message (placeholder for actual WhatsApp service integration)."""
        # TODO: Integrate with WhatsApp Business API
        logger.info(f"WhatsApp sent to {event.customer.phone_number}: {event.message_persian}")
        return True


class CustomerLoyaltyService:
    """
    Service for managing customer loyalty program and VIP tiers.
    """
    
    def __init__(self, tenant):
        self.tenant = tenant
    
    def get_active_loyalty_program(self) -> Optional[CustomerLoyaltyProgram]:
        """Get the active loyalty program for the tenant."""
        return CustomerLoyaltyProgram.objects.filter(
            tenant=self.tenant,
            is_active=True
        ).first()
    
    def calculate_customer_tier(self, customer: Customer) -> str:
        """Calculate appropriate VIP tier for customer based on total purchases."""
        program = self.get_active_loyalty_program()
        if not program:
            return 'regular'
        
        return program.get_vip_tier(customer.total_purchases)
    
    def update_customer_tier(self, customer: Customer) -> Optional[CustomerVIPTier]:
        """Update customer's VIP tier if they qualify for upgrade."""
        program = self.get_active_loyalty_program()
        if not program:
            return None
        
        new_tier = self.calculate_customer_tier(customer)
        
        # Get current tier
        current_tier_record = CustomerVIPTier.objects.filter(
            customer=customer,
            is_current=True
        ).first()
        
        current_tier = current_tier_record.tier if current_tier_record else 'regular'
        
        # Check if upgrade is needed
        tier_hierarchy = ['regular', 'bronze', 'silver', 'gold', 'platinum']
        if tier_hierarchy.index(new_tier) > tier_hierarchy.index(current_tier):
            # Upgrade needed
            
            # Deactivate current tier
            if current_tier_record:
                current_tier_record.is_current = False
                current_tier_record.save()
            
            # Create new tier record
            benefits = program.get_tier_benefits(new_tier)
            new_tier_record = CustomerVIPTier.objects.create(
                customer=customer,
                loyalty_program=program,
                tier=new_tier,
                previous_tier=current_tier,
                total_purchases_at_upgrade=customer.total_purchases,
                points_balance_at_upgrade=customer.loyalty_points,
                effective_date=timezone.now().date(),
                discount_percentage=benefits['discount_percentage'],
                bonus_points_multiplier=benefits['bonus_points_multiplier']
            )
            
            # Update customer VIP status
            customer.is_vip = new_tier != 'regular'
            customer.customer_type = 'vip' if customer.is_vip else 'individual'
            customer.save(update_fields=['is_vip', 'customer_type', 'updated_at'])
            
            # Create VIP upgrade engagement event
            self._create_vip_upgrade_event(customer, new_tier, current_tier)
            
            logger.info(f"Upgraded customer {customer.full_persian_name} from {current_tier} to {new_tier}")
            return new_tier_record
        
        return None
    
    def process_purchase_loyalty(self, customer: Customer, purchase_amount: float) -> Dict:
        """
        Process loyalty points and tier updates for a purchase.
        
        Returns:
            Dictionary with points earned, tier changes, and discounts applied
        """
        program = self.get_active_loyalty_program()
        if not program:
            return {'points_earned': 0, 'tier_changed': False, 'discount_applied': 0}
        
        # Calculate base points
        base_points = program.calculate_points_earned(purchase_amount)
        
        # Apply tier multiplier if customer has VIP tier
        current_tier = CustomerVIPTier.objects.filter(
            customer=customer,
            is_current=True
        ).first()
        
        if current_tier and current_tier.is_active:
            final_points = current_tier.calculate_bonus_points(base_points)
            discount_amount = current_tier.calculate_discount(purchase_amount)
            
            # Record benefit usage
            if discount_amount > 0:
                current_tier.record_benefit_usage(discount_amount)
        else:
            final_points = base_points
            discount_amount = 0
        
        # Award points to customer
        customer.add_loyalty_points(final_points, f"Purchase reward - {purchase_amount:,.0f} Toman")
        
        # Update purchase statistics
        customer.update_purchase_stats(purchase_amount)
        
        # Check for tier upgrade
        tier_upgrade = self.update_customer_tier(customer)
        
        return {
            'points_earned': final_points,
            'tier_changed': tier_upgrade is not None,
            'new_tier': tier_upgrade.tier if tier_upgrade else None,
            'discount_applied': discount_amount
        }
    
    def create_special_offer(self, customer: Customer, offer_type: str, **kwargs) -> CustomerSpecialOffer:
        """Create a special offer for a customer."""
        
        # Default offer configurations
        offer_configs = {
            'birthday_discount': {
                'title': 'Birthday Special Discount',
                'title_persian': 'تخفیف ویژه تولد',
                'description': 'Special birthday discount just for you!',
                'description_persian': 'تخفیف ویژه تولد مخصوص شما!',
                'discount_percentage': 15,
                'valid_days': 7,
            },
            'anniversary_gift': {
                'title': 'Anniversary Gift',
                'title_persian': 'هدیه سالگرد',
                'description': 'Thank you for being our loyal customer!',
                'description_persian': 'از اینکه مشتری وفادار ما هستید متشکریم!',
                'discount_percentage': 10,
                'valid_days': 14,
            },
            'vip_exclusive': {
                'title': 'VIP Exclusive Offer',
                'title_persian': 'پیشنهاد ویژه VIP',
                'description': 'Exclusive offer for our VIP customers',
                'description_persian': 'پیشنهاد انحصاری برای مشتریان VIP ما',
                'discount_percentage': 20,
                'valid_days': 30,
            }
        }
        
        config = offer_configs.get(offer_type, offer_configs['birthday_discount'])
        config.update(kwargs)  # Override with provided kwargs
        
        # Calculate validity period
        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=config.get('valid_days', 7))
        
        offer = CustomerSpecialOffer.objects.create(
            customer=customer,
            offer_type=offer_type,
            title=config['title'],
            title_persian=config['title_persian'],
            description=config['description'],
            description_persian=config['description_persian'],
            discount_percentage=config.get('discount_percentage', 0),
            discount_amount=config.get('discount_amount', 0),
            minimum_purchase=config.get('minimum_purchase', 0),
            valid_from=valid_from,
            valid_until=valid_until,
            max_uses=config.get('max_uses', 1)
        )
        
        logger.info(f"Created {offer_type} offer for {customer.full_persian_name}")
        return offer
    
    def process_referral(self, referrer: Customer, referred_customer_data: Dict) -> CustomerReferral:
        """Process a customer referral."""
        
        # Create referred customer (this would typically be done in customer creation flow)
        # For now, we'll assume the customer already exists
        
        # Generate referral code
        referral = CustomerReferral(
            referrer=referrer,
            referral_date=timezone.now().date()
        )
        referral.referral_code = referral.generate_referral_code()
        referral.save()
        
        logger.info(f"Created referral {referral.referral_code} for {referrer.full_persian_name}")
        return referral
    
    def _create_vip_upgrade_event(self, customer: Customer, new_tier: str, old_tier: str):
        """Create engagement event for VIP tier upgrade."""
        
        tier_names_persian = {
            'bronze': 'برنز',
            'silver': 'نقره‌ای',
            'gold': 'طلایی',
            'platinum': 'پلاتینیوم'
        }
        
        new_tier_persian = tier_names_persian.get(new_tier, new_tier)
        
        CustomerEngagementEvent.objects.create(
            customer=customer,
            event_type='vip_upgrade',
            title=f"VIP Tier Upgrade - {customer.full_persian_name}",
            title_persian=f"ارتقاء سطح VIP - {customer.full_persian_name}",
            message=f"Congratulations! You've been upgraded to {new_tier.title()} VIP tier!",
            message_persian=f"تبریک! شما به سطح VIP {new_tier_persian} ارتقاء یافتید!",
            scheduled_date=timezone.now(),
            delivery_method='sms',
            bonus_points_awarded=1000  # Bonus points for tier upgrade
        )