"""
Tests for customer loyalty and engagement system.
"""
import pytest
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from datetime import datetime, timedelta, date
import jdatetime
from decimal import Decimal

from zargar.tenants.models import Tenant, Domain
from zargar.customers.models import Customer
from zargar.customers.loyalty_models import (
    CustomerLoyaltyProgram,
    CustomerEngagementEvent,
    CustomerVIPTier,
    CustomerReferral,
    CustomerSpecialOffer
)
from zargar.customers.engagement_services import (
    CustomerEngagementService,
    CustomerLoyaltyService
)

User = get_user_model()


class CustomerLoyaltyEngagementTestCase(TenantTestCase):
    """Base test case for loyalty and engagement tests."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create tenant
        cls.tenant = Tenant(
            name="Test Jewelry Shop",
            schema_name="test_jewelry",
            is_active=True
        )
        cls.tenant.save()
        
        # Create domain
        cls.domain = Domain(
            domain="testjewelry.zargar.local",
            tenant=cls.tenant,
            is_primary=True
        )
        cls.domain.save()
    
    def setUp(self):
        super().setUp()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testowner',
            email='owner@testjewelry.com',
            password='testpass123',
            role='owner'
        )
        
        # Create test customers
        self.customer1 = Customer.objects.create(
            first_name="Ahmad",
            last_name="Rezaei",
            persian_first_name="احمد",
            persian_last_name="رضایی",
            phone_number="09123456789",
            email="ahmad@example.com",
            birth_date=date(1985, 5, 15),
            birth_date_shamsi="1364/02/25",
            total_purchases=Decimal('15000000'),  # 15 million Toman
            loyalty_points=1500,
            created_by=self.user
        )
        
        self.customer2 = Customer.objects.create(
            first_name="Maryam",
            last_name="Hosseini",
            persian_first_name="مریم",
            persian_last_name="حسینی",
            phone_number="09987654321",
            email="maryam@example.com",
            birth_date=date(1990, 8, 20),
            birth_date_shamsi="1369/05/29",
            total_purchases=Decimal('60000000'),  # 60 million Toman
            loyalty_points=6000,
            is_vip=True,
            created_by=self.user
        )
        
        # Create loyalty program
        self.loyalty_program = CustomerLoyaltyProgram.objects.create(
            name="Test Loyalty Program",
            name_persian="برنامه وفاداری تست",
            description="Test loyalty program",
            description_persian="برنامه وفاداری تست",
            program_type='hybrid',
            start_date=timezone.now().date(),
            points_per_toman=Decimal('0.1'),  # 1 point per 10 Toman
            toman_per_point=Decimal('10.0'),  # Each point worth 10 Toman
            vip_threshold_bronze=Decimal('10000000'),   # 10 million
            vip_threshold_silver=Decimal('25000000'),   # 25 million
            vip_threshold_gold=Decimal('50000000'),     # 50 million
            vip_threshold_platinum=Decimal('100000000'), # 100 million
            birthday_bonus_points=1000,
            anniversary_bonus_points=500,
            nowruz_bonus_points=2000,
            yalda_bonus_points=1500,
            wedding_bonus_points=3000,
            referral_bonus_points=2000,
            created_by=self.user
        )
        
        # Initialize services
        self.engagement_service = CustomerEngagementService(self.tenant)
        self.loyalty_service = CustomerLoyaltyService(self.tenant)


class CustomerLoyaltyProgramModelTest(CustomerLoyaltyEngagementTestCase):
    """Test CustomerLoyaltyProgram model."""
    
    def test_loyalty_program_creation(self):
        """Test creating a loyalty program."""
        self.assertEqual(self.loyalty_program.name_persian, "برنامه وفاداری تست")
        self.assertEqual(self.loyalty_program.program_type, 'hybrid')
        self.assertTrue(self.loyalty_program.is_active)
    
    def test_get_vip_tier(self):
        """Test VIP tier calculation."""
        # Test different purchase amounts
        self.assertEqual(
            self.loyalty_program.get_vip_tier(Decimal('5000000')), 
            'regular'
        )
        self.assertEqual(
            self.loyalty_program.get_vip_tier(Decimal('15000000')), 
            'bronze'
        )
        self.assertEqual(
            self.loyalty_program.get_vip_tier(Decimal('30000000')), 
            'silver'
        )
        self.assertEqual(
            self.loyalty_program.get_vip_tier(Decimal('60000000')), 
            'gold'
        )
        self.assertEqual(
            self.loyalty_program.get_vip_tier(Decimal('120000000')), 
            'platinum'
        )
    
    def test_calculate_points_earned(self):
        """Test points calculation."""
        # 1 point per 10 Toman
        points = self.loyalty_program.calculate_points_earned(Decimal('100000'))
        self.assertEqual(points, 10000)
        
        points = self.loyalty_program.calculate_points_earned(Decimal('50000'))
        self.assertEqual(points, 5000)
    
    def test_calculate_points_value(self):
        """Test points value calculation."""
        # Each point worth 10 Toman
        value = self.loyalty_program.calculate_points_value(1000)
        self.assertEqual(value, Decimal('10000'))
    
    def test_get_tier_benefits(self):
        """Test tier benefits retrieval."""
        bronze_benefits = self.loyalty_program.get_tier_benefits('bronze')
        self.assertEqual(bronze_benefits['discount_percentage'], 2)
        self.assertEqual(bronze_benefits['bonus_points_multiplier'], 1.1)
        
        gold_benefits = self.loyalty_program.get_tier_benefits('gold')
        self.assertEqual(gold_benefits['discount_percentage'], 8)
        self.assertEqual(gold_benefits['bonus_points_multiplier'], 1.5)
        self.assertTrue(gold_benefits['exclusive_events'])


class CustomerEngagementEventModelTest(CustomerLoyaltyEngagementTestCase):
    """Test CustomerEngagementEvent model."""
    
    def test_engagement_event_creation(self):
        """Test creating an engagement event."""
        event = CustomerEngagementEvent.objects.create(
            customer=self.customer1,
            event_type='birthday',
            title="Birthday Reminder",
            title_persian="یادآوری تولد",
            message="Happy Birthday!",
            message_persian="تولدت مبارک!",
            scheduled_date=timezone.now() + timedelta(days=1),
            delivery_method='sms',
            bonus_points_awarded=1000
        )
        
        self.assertEqual(event.customer, self.customer1)
        self.assertEqual(event.event_type, 'birthday')
        self.assertEqual(event.status, 'pending')
        self.assertEqual(event.bonus_points_awarded, 1000)
    
    def test_mark_as_sent(self):
        """Test marking event as sent."""
        event = CustomerEngagementEvent.objects.create(
            customer=self.customer1,
            event_type='birthday',
            title="Birthday Reminder",
            message="Happy Birthday!",
            scheduled_date=timezone.now()
        )
        
        self.assertEqual(event.status, 'pending')
        self.assertIsNone(event.sent_date)
        
        event.mark_as_sent()
        
        self.assertEqual(event.status, 'sent')
        self.assertIsNotNone(event.sent_date)
    
    def test_record_response(self):
        """Test recording customer response."""
        event = CustomerEngagementEvent.objects.create(
            customer=self.customer1,
            event_type='birthday',
            title="Birthday Reminder",
            message="Happy Birthday!",
            scheduled_date=timezone.now()
        )
        
        self.assertFalse(event.is_responded)
        self.assertIsNone(event.response_date)
        
        event.record_response("Thank you for the wishes!")
        
        self.assertTrue(event.is_responded)
        self.assertIsNotNone(event.response_date)
        self.assertEqual(event.response_notes, "Thank you for the wishes!")


class CustomerVIPTierModelTest(CustomerLoyaltyEngagementTestCase):
    """Test CustomerVIPTier model."""
    
    def test_vip_tier_creation(self):
        """Test creating a VIP tier record."""
        tier = CustomerVIPTier.objects.create(
            customer=self.customer2,
            loyalty_program=self.loyalty_program,
            tier='gold',
            previous_tier='silver',
            total_purchases_at_upgrade=Decimal('60000000'),
            points_balance_at_upgrade=6000,
            effective_date=timezone.now().date(),
            discount_percentage=Decimal('8.0'),
            bonus_points_multiplier=Decimal('1.5')
        )
        
        self.assertEqual(tier.customer, self.customer2)
        self.assertEqual(tier.tier, 'gold')
        self.assertEqual(tier.previous_tier, 'silver')
        self.assertTrue(tier.is_current)
        self.assertTrue(tier.is_active)
    
    def test_calculate_discount(self):
        """Test discount calculation."""
        tier = CustomerVIPTier.objects.create(
            customer=self.customer2,
            loyalty_program=self.loyalty_program,
            tier='gold',
            total_purchases_at_upgrade=Decimal('60000000'),
            effective_date=timezone.now().date(),
            discount_percentage=Decimal('8.0'),
            bonus_points_multiplier=Decimal('1.5')
        )
        
        discount = tier.calculate_discount(Decimal('1000000'))  # 1 million Toman
        self.assertEqual(discount, Decimal('80000'))  # 8% discount
    
    def test_calculate_bonus_points(self):
        """Test bonus points calculation with multiplier."""
        tier = CustomerVIPTier.objects.create(
            customer=self.customer2,
            loyalty_program=self.loyalty_program,
            tier='gold',
            total_purchases_at_upgrade=Decimal('60000000'),
            effective_date=timezone.now().date(),
            discount_percentage=Decimal('8.0'),
            bonus_points_multiplier=Decimal('1.5')
        )
        
        bonus_points = tier.calculate_bonus_points(1000)
        self.assertEqual(bonus_points, 1500)  # 1.5x multiplier
    
    def test_record_benefit_usage(self):
        """Test recording benefit usage."""
        tier = CustomerVIPTier.objects.create(
            customer=self.customer2,
            loyalty_program=self.loyalty_program,
            tier='gold',
            total_purchases_at_upgrade=Decimal('60000000'),
            effective_date=timezone.now().date(),
            discount_percentage=Decimal('8.0'),
            bonus_points_multiplier=Decimal('1.5')
        )
        
        self.assertEqual(tier.benefits_used_count, 0)
        self.assertEqual(tier.total_savings, Decimal('0'))
        
        tier.record_benefit_usage(Decimal('50000'))
        
        self.assertEqual(tier.benefits_used_count, 1)
        self.assertEqual(tier.total_savings, Decimal('50000'))


class CustomerEngagementServiceTest(CustomerLoyaltyEngagementTestCase):
    """Test CustomerEngagementService."""
    
    def test_create_birthday_reminders(self):
        """Test creating birthday reminders."""
        # Set customer's birthday to 7 days from now (in Shamsi calendar)
        future_date_shamsi = jdatetime.date.today() + jdatetime.timedelta(days=7)
        self.customer1.birth_date_shamsi = future_date_shamsi.strftime('%Y/%m/%d')
        self.customer1.save()
        
        # Create birthday reminders
        events = self.engagement_service.create_birthday_reminders(days_ahead=7)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].customer, self.customer1)
        self.assertEqual(events[0].event_type, 'birthday')
        self.assertEqual(events[0].bonus_points_awarded, 1000)
        self.assertIn('تولدت مبارک', events[0].message_persian)
    
    def test_create_anniversary_reminders(self):
        """Test creating anniversary reminders."""
        # Set customer creation date to 1 year ago + 7 days from now
        target_date = timezone.now().date() + timedelta(days=7)
        anniversary_date = target_date.replace(year=target_date.year - 1)
        
        self.customer1.created_at = timezone.make_aware(
            datetime.combine(anniversary_date, datetime.min.time())
        )
        self.customer1.save()
        
        # Create anniversary reminders
        events = self.engagement_service.create_anniversary_reminders(days_ahead=7)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].customer, self.customer1)
        self.assertEqual(events[0].event_type, 'anniversary')
        self.assertEqual(events[0].bonus_points_awarded, 500)
        self.assertIn('سالگرد', events[0].title_persian)
    
    def test_create_cultural_event_reminders(self):
        """Test creating cultural event reminders."""
        # Create Nowruz reminders (only for VIP customers)
        events = self.engagement_service.create_cultural_event_reminders('nowruz')
        
        # Should create event for VIP customer (customer2) but not regular customer (customer1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].customer, self.customer2)
        self.assertEqual(events[0].event_type, 'nowruz')
        self.assertEqual(events[0].bonus_points_awarded, 2000)
        self.assertIn('نوروز', events[0].title_persian)
    
    def test_generate_gift_suggestions(self):
        """Test gift suggestion generation."""
        suggestions = self.engagement_service._generate_gift_suggestions(
            self.customer1, 
            occasion='birthday'
        )
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        self.assertLessEqual(len(suggestions), 5)
        
        # Check suggestion structure
        for suggestion in suggestions:
            self.assertIn('type', suggestion)
            self.assertIn('name_persian', suggestion)
            self.assertIn('price_range', suggestion)
    
    def test_generate_vip_gift_suggestions(self):
        """Test gift suggestions for VIP customers include premium items."""
        suggestions = self.engagement_service._generate_gift_suggestions(
            self.customer2,  # VIP customer
            occasion='anniversary'
        )
        
        # VIP customers should get premium suggestions
        suggestion_types = [s['type'] for s in suggestions]
        self.assertIn('diamond_ring', suggestion_types)


class CustomerLoyaltyServiceTest(CustomerLoyaltyEngagementTestCase):
    """Test CustomerLoyaltyService."""
    
    def test_get_active_loyalty_program(self):
        """Test getting active loyalty program."""
        program = self.loyalty_service.get_active_loyalty_program()
        
        self.assertIsNotNone(program)
        self.assertEqual(program, self.loyalty_program)
        self.assertTrue(program.is_active)
    
    def test_calculate_customer_tier(self):
        """Test calculating customer tier."""
        # Customer1 has 15M Toman purchases -> should be bronze
        tier = self.loyalty_service.calculate_customer_tier(self.customer1)
        self.assertEqual(tier, 'bronze')
        
        # Customer2 has 60M Toman purchases -> should be gold
        tier = self.loyalty_service.calculate_customer_tier(self.customer2)
        self.assertEqual(tier, 'gold')
    
    def test_update_customer_tier(self):
        """Test updating customer tier."""
        # Customer1 should be upgraded to bronze
        tier_record = self.loyalty_service.update_customer_tier(self.customer1)
        
        self.assertIsNotNone(tier_record)
        self.assertEqual(tier_record.tier, 'bronze')
        self.assertEqual(tier_record.previous_tier, 'regular')
        self.assertTrue(tier_record.is_current)
        
        # Check that customer VIP status was updated
        self.customer1.refresh_from_db()
        self.assertTrue(self.customer1.is_vip)
        self.assertEqual(self.customer1.customer_type, 'vip')
    
    def test_process_purchase_loyalty(self):
        """Test processing loyalty for a purchase."""
        purchase_amount = Decimal('1000000')  # 1 million Toman
        
        # Process purchase
        result = self.loyalty_service.process_purchase_loyalty(
            self.customer1, 
            purchase_amount
        )
        
        # Check results
        expected_points = int(purchase_amount * self.loyalty_program.points_per_toman)
        self.assertEqual(result['points_earned'], expected_points)
        
        # Check customer was updated
        self.customer1.refresh_from_db()
        self.assertEqual(
            self.customer1.total_purchases, 
            Decimal('16000000')  # Original 15M + 1M
        )
        self.assertIsNotNone(self.customer1.last_purchase_date)
    
    def test_process_purchase_with_vip_benefits(self):
        """Test processing purchase with VIP tier benefits."""
        # Create VIP tier for customer2
        tier = CustomerVIPTier.objects.create(
            customer=self.customer2,
            loyalty_program=self.loyalty_program,
            tier='gold',
            total_purchases_at_upgrade=Decimal('60000000'),
            effective_date=timezone.now().date(),
            discount_percentage=Decimal('8.0'),
            bonus_points_multiplier=Decimal('1.5')
        )
        
        purchase_amount = Decimal('1000000')  # 1 million Toman
        
        # Process purchase
        result = self.loyalty_service.process_purchase_loyalty(
            self.customer2, 
            purchase_amount
        )
        
        # Check VIP benefits were applied
        base_points = int(purchase_amount * self.loyalty_program.points_per_toman)
        expected_points = int(base_points * tier.bonus_points_multiplier)
        
        self.assertEqual(result['points_earned'], expected_points)
        self.assertEqual(result['discount_applied'], Decimal('80000'))  # 8% of 1M
        
        # Check tier benefit usage was recorded
        tier.refresh_from_db()
        self.assertEqual(tier.benefits_used_count, 1)
        self.assertEqual(tier.total_savings, Decimal('80000'))
    
    def test_create_special_offer(self):
        """Test creating special offers."""
        offer = self.loyalty_service.create_special_offer(
            self.customer1,
            'birthday_discount',
            discount_percentage=20,
            valid_days=10
        )
        
        self.assertEqual(offer.customer, self.customer1)
        self.assertEqual(offer.offer_type, 'birthday_discount')
        self.assertEqual(offer.discount_percentage, Decimal('20'))
        self.assertEqual(offer.status, 'active')
        self.assertTrue(offer.is_valid)
    
    def test_process_referral(self):
        """Test processing customer referral."""
        referral = self.loyalty_service.process_referral(
            self.customer1,
            {'name': 'New Customer', 'phone': '09111111111'}
        )
        
        self.assertEqual(referral.referrer, self.customer1)
        self.assertEqual(referral.status, 'pending')
        self.assertIsNotNone(referral.referral_code)
        self.assertEqual(len(referral.referral_code), 8)


class CustomerSpecialOfferModelTest(CustomerLoyaltyEngagementTestCase):
    """Test CustomerSpecialOffer model."""
    
    def test_special_offer_creation(self):
        """Test creating a special offer."""
        offer = CustomerSpecialOffer.objects.create(
            customer=self.customer1,
            offer_type='birthday_discount',
            title='Birthday Special',
            title_persian='پیشنهاد ویژه تولد',
            description='Special birthday discount',
            description_persian='تخفیف ویژه تولد',
            discount_percentage=Decimal('15'),
            minimum_purchase=Decimal('500000'),
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=7),
            max_uses=1
        )
        
        self.assertEqual(offer.customer, self.customer1)
        self.assertEqual(offer.offer_type, 'birthday_discount')
        self.assertTrue(offer.is_valid)
    
    def test_calculate_discount(self):
        """Test discount calculation."""
        offer = CustomerSpecialOffer.objects.create(
            customer=self.customer1,
            offer_type='birthday_discount',
            title='Birthday Special',
            discount_percentage=Decimal('15'),
            minimum_purchase=Decimal('500000'),
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=7)
        )
        
        # Purchase above minimum
        discount = offer.calculate_discount(Decimal('1000000'))
        self.assertEqual(discount, Decimal('150000'))  # 15% of 1M
        
        # Purchase below minimum
        discount = offer.calculate_discount(Decimal('300000'))
        self.assertEqual(discount, 0)
    
    def test_use_offer(self):
        """Test using an offer."""
        offer = CustomerSpecialOffer.objects.create(
            customer=self.customer1,
            offer_type='birthday_discount',
            title='Birthday Special',
            discount_percentage=Decimal('15'),
            minimum_purchase=Decimal('500000'),
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=7),
            max_uses=1
        )
        
        self.assertEqual(offer.uses_count, 0)
        self.assertEqual(offer.status, 'active')
        
        # Use the offer
        success = offer.use_offer(Decimal('1000000'))
        
        self.assertTrue(success)
        self.assertEqual(offer.uses_count, 1)
        self.assertEqual(offer.status, 'used')
        self.assertEqual(offer.used_amount, Decimal('150000'))
        self.assertIsNotNone(offer.used_date)


class CustomerReferralModelTest(CustomerLoyaltyEngagementTestCase):
    """Test CustomerReferral model."""
    
    def test_referral_creation(self):
        """Test creating a referral."""
        referral = CustomerReferral.objects.create(
            referrer=self.customer1,
            referred_customer=self.customer2,
            referral_date=timezone.now().date()
        )
        referral.referral_code = referral.generate_referral_code()
        referral.save()
        
        self.assertEqual(referral.referrer, self.customer1)
        self.assertEqual(referral.referred_customer, self.customer2)
        self.assertEqual(referral.status, 'pending')
        self.assertIsNotNone(referral.referral_code)
    
    def test_complete_referral(self):
        """Test completing a referral."""
        referral = CustomerReferral.objects.create(
            referrer=self.customer1,
            referred_customer=self.customer2,
            referral_date=timezone.now().date()
        )
        referral.referral_code = referral.generate_referral_code()
        referral.save()
        
        initial_points = self.customer1.loyalty_points
        
        # Complete the referral
        success = referral.complete_referral(Decimal('2000000'))
        
        self.assertTrue(success)
        self.assertEqual(referral.status, 'completed')
        self.assertIsNotNone(referral.first_purchase_date)
        self.assertEqual(referral.bonus_points_awarded, 2000)
        
        # Check referrer got bonus points
        self.customer1.refresh_from_db()
        self.assertEqual(
            self.customer1.loyalty_points, 
            initial_points + 2000
        )
    
    def test_generate_referral_code(self):
        """Test referral code generation."""
        referral = CustomerReferral()
        code = referral.generate_referral_code()
        
        self.assertIsNotNone(code)
        self.assertEqual(len(code), 8)
        self.assertTrue(code.isalnum())
        self.assertTrue(code.isupper())


@pytest.mark.django_db
class CustomerLoyaltyIntegrationTest(CustomerLoyaltyEngagementTestCase):
    """Integration tests for the complete loyalty system."""
    
    def test_complete_customer_journey(self):
        """Test complete customer loyalty journey."""
        # 1. Customer starts as regular
        self.assertEqual(self.customer1.customer_type, 'individual')
        self.assertFalse(self.customer1.is_vip)
        
        # 2. Customer makes purchases and earns points
        for i in range(5):
            result = self.loyalty_service.process_purchase_loyalty(
                self.customer1, 
                Decimal('5000000')  # 5M Toman each
            )
            self.assertGreater(result['points_earned'], 0)
        
        # 3. Customer should now be upgraded to higher tier
        self.customer1.refresh_from_db()
        self.assertGreater(self.customer1.total_purchases, Decimal('40000000'))
        self.assertTrue(self.customer1.is_vip)
        
        # 4. Check VIP tier record was created
        vip_tier = CustomerVIPTier.objects.filter(
            customer=self.customer1,
            is_current=True
        ).first()
        self.assertIsNotNone(vip_tier)
        self.assertIn(vip_tier.tier, ['bronze', 'silver', 'gold', 'platinum'])
        
        # 5. Create birthday reminder
        future_date_shamsi = jdatetime.date.today() + jdatetime.timedelta(days=7)
        self.customer1.birth_date_shamsi = future_date_shamsi.strftime('%Y/%m/%d')
        self.customer1.save()
        
        events = self.engagement_service.create_birthday_reminders(days_ahead=7)
        self.assertEqual(len(events), 1)
        
        # 6. Create special offer for birthday
        offer = self.loyalty_service.create_special_offer(
            self.customer1,
            'birthday_discount'
        )
        self.assertTrue(offer.is_valid)
        
        # 7. Use the offer
        success = offer.use_offer(Decimal('2000000'))
        self.assertTrue(success)
    
    def test_loyalty_program_statistics(self):
        """Test loyalty program statistics calculation."""
        # Create various tier customers
        customers = []
        
        # Create bronze customers
        for i in range(3):
            customer = Customer.objects.create(
                first_name=f"Customer{i}",
                last_name="Bronze",
                phone_number=f"0912345{i:04d}",
                total_purchases=Decimal('15000000'),
                created_by=self.user
            )
            customers.append(customer)
            self.loyalty_service.update_customer_tier(customer)
        
        # Create silver customers
        for i in range(2):
            customer = Customer.objects.create(
                first_name=f"Customer{i}",
                last_name="Silver",
                phone_number=f"0912346{i:04d}",
                total_purchases=Decimal('30000000'),
                created_by=self.user
            )
            customers.append(customer)
            self.loyalty_service.update_customer_tier(customer)
        
        # Check tier distribution
        bronze_count = CustomerVIPTier.objects.filter(
            customer__tenant=self.tenant,
            tier='bronze',
            is_current=True
        ).count()
        
        silver_count = CustomerVIPTier.objects.filter(
            customer__tenant=self.tenant,
            tier='silver',
            is_current=True
        ).count()
        
        self.assertEqual(bronze_count, 3)
        self.assertEqual(silver_count, 2)
    
    def test_cultural_events_seasonal_creation(self):
        """Test seasonal cultural event creation."""
        # Test Nowruz (Spring)
        nowruz_events = self.engagement_service.create_cultural_event_reminders('nowruz')
        self.assertGreater(len(nowruz_events), 0)
        
        # Test Yalda (Winter)
        yalda_events = self.engagement_service.create_cultural_event_reminders('yalda')
        self.assertGreater(len(yalda_events), 0)
        
        # Test Mehregan (Autumn)
        mehregan_events = self.engagement_service.create_cultural_event_reminders('mehregan')
        self.assertGreater(len(mehregan_events), 0)
        
        # All events should be for VIP customers only
        all_events = nowruz_events + yalda_events + mehregan_events
        for event in all_events:
            self.assertTrue(event.customer.is_vip)


if __name__ == '__main__':
    pytest.main([__file__])