"""
Customer loyalty and engagement system models for zargar project.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from zargar.core.models import TenantAwareModel
from .models import Customer
import jdatetime


class CustomerLoyaltyProgram(TenantAwareModel):
    """
    Customer loyalty program configuration with Persian cultural considerations.
    """
    PROGRAM_TYPES = [
        ('points_based', _('Points Based')),
        ('tier_based', _('Tier Based')),
        ('hybrid', _('Hybrid (Points + Tiers)')),
    ]
    
    CULTURAL_EVENTS = [
        ('nowruz', _('Nowruz (Persian New Year)')),
        ('yalda', _('Yalda Night')),
        ('mehregan', _('Mehregan Festival')),
        ('birthday', _('Customer Birthday')),
        ('anniversary', _('Purchase Anniversary')),
        ('wedding', _('Wedding Anniversary')),
    ]
    
    # Basic program information
    name = models.CharField(
        max_length=100,
        verbose_name=_('Program Name')
    )
    name_persian = models.CharField(
        max_length=100,
        verbose_name=_('Persian Program Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    description_persian = models.TextField(
        blank=True,
        verbose_name=_('Persian Description')
    )
    
    # Program configuration
    program_type = models.CharField(
        max_length=20,
        choices=PROGRAM_TYPES,
        default='points_based',
        verbose_name=_('Program Type')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    start_date = models.DateField(
        verbose_name=_('Start Date')
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('End Date')
    )
    
    # Points configuration
    points_per_toman = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0.01)],
        verbose_name=_('Points per Toman Spent'),
        help_text=_('How many points customer earns per Toman spent')
    )
    toman_per_point = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0.01)],
        verbose_name=_('Toman Value per Point'),
        help_text=_('How much each point is worth in Toman when redeemed')
    )
    
    # VIP tier thresholds (in Toman)
    vip_threshold_bronze = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=10000000,  # 10 million Toman
        verbose_name=_('Bronze VIP Threshold (Toman)')
    )
    vip_threshold_silver = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=25000000,  # 25 million Toman
        verbose_name=_('Silver VIP Threshold (Toman)')
    )
    vip_threshold_gold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=50000000,  # 50 million Toman
        verbose_name=_('Gold VIP Threshold (Toman)')
    )
    vip_threshold_platinum = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=100000000,  # 100 million Toman
        verbose_name=_('Platinum VIP Threshold (Toman)')
    )
    
    # Bonus points for special occasions
    birthday_bonus_points = models.IntegerField(
        default=1000,
        validators=[MinValueValidator(0)],
        verbose_name=_('Birthday Bonus Points')
    )
    anniversary_bonus_points = models.IntegerField(
        default=500,
        validators=[MinValueValidator(0)],
        verbose_name=_('Anniversary Bonus Points')
    )
    nowruz_bonus_points = models.IntegerField(
        default=2000,
        validators=[MinValueValidator(0)],
        verbose_name=_('Nowruz Bonus Points')
    )
    yalda_bonus_points = models.IntegerField(
        default=1500,
        validators=[MinValueValidator(0)],
        verbose_name=_('Yalda Night Bonus Points')
    )
    wedding_bonus_points = models.IntegerField(
        default=3000,
        validators=[MinValueValidator(0)],
        verbose_name=_('Wedding Anniversary Bonus Points')
    )
    
    # Referral program
    referral_bonus_points = models.IntegerField(
        default=2000,
        validators=[MinValueValidator(0)],
        verbose_name=_('Referral Bonus Points'),
        help_text=_('Points awarded for successful customer referrals')
    )
    
    # Point expiration
    points_expire_months = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        verbose_name=_('Points Expiration (Months)'),
        help_text=_('Number of months after which unused points expire')
    )
    
    class Meta:
        verbose_name = _('Customer Loyalty Program')
        verbose_name_plural = _('Customer Loyalty Programs')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name_persian or self.name
    
    def get_vip_tier(self, total_purchases):
        """Determine VIP tier based on total purchases."""
        if total_purchases >= self.vip_threshold_platinum:
            return 'platinum'
        elif total_purchases >= self.vip_threshold_gold:
            return 'gold'
        elif total_purchases >= self.vip_threshold_silver:
            return 'silver'
        elif total_purchases >= self.vip_threshold_bronze:
            return 'bronze'
        else:
            return 'regular'
    
    def calculate_points_earned(self, purchase_amount):
        """Calculate points earned for a purchase amount."""
        return int(purchase_amount * self.points_per_toman)
    
    def calculate_points_value(self, points):
        """Calculate Toman value of points."""
        return points * self.toman_per_point
    
    def get_tier_benefits(self, tier):
        """Get benefits for a specific VIP tier."""
        benefits = {
            'regular': {
                'discount_percentage': 0,
                'bonus_points_multiplier': 1.0,
                'priority_service': False,
                'exclusive_events': False,
            },
            'bronze': {
                'discount_percentage': 2,
                'bonus_points_multiplier': 1.1,
                'priority_service': False,
                'exclusive_events': False,
            },
            'silver': {
                'discount_percentage': 5,
                'bonus_points_multiplier': 1.25,
                'priority_service': True,
                'exclusive_events': False,
            },
            'gold': {
                'discount_percentage': 8,
                'bonus_points_multiplier': 1.5,
                'priority_service': True,
                'exclusive_events': True,
            },
            'platinum': {
                'discount_percentage': 12,
                'bonus_points_multiplier': 2.0,
                'priority_service': True,
                'exclusive_events': True,
            },
        }
        return benefits.get(tier, benefits['regular'])


class CustomerEngagementEvent(TenantAwareModel):
    """
    Track customer engagement events and reminders.
    """
    EVENT_TYPES = [
        ('birthday', _('Birthday')),
        ('anniversary', _('Purchase Anniversary')),
        ('wedding_anniversary', _('Wedding Anniversary')),
        ('nowruz', _('Nowruz Greeting')),
        ('yalda', _('Yalda Night Greeting')),
        ('mehregan', _('Mehregan Festival')),
        ('follow_up', _('Follow-up Reminder')),
        ('special_offer', _('Special Offer')),
        ('vip_upgrade', _('VIP Tier Upgrade')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    DELIVERY_METHODS = [
        ('sms', _('SMS')),
        ('email', _('Email')),
        ('phone_call', _('Phone Call')),
        ('in_person', _('In Person')),
        ('whatsapp', _('WhatsApp')),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='engagement_events',
        verbose_name=_('Customer')
    )
    
    # Event details
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        verbose_name=_('Event Type')
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_('Title')
    )
    title_persian = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Persian Title')
    )
    message = models.TextField(
        verbose_name=_('Message')
    )
    message_persian = models.TextField(
        blank=True,
        verbose_name=_('Persian Message')
    )
    
    # Scheduling
    scheduled_date = models.DateTimeField(
        verbose_name=_('Scheduled Date')
    )
    sent_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Sent Date')
    )
    
    # Delivery
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHODS,
        default='sms',
        verbose_name=_('Delivery Method')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    
    # Response tracking
    is_responded = models.BooleanField(
        default=False,
        verbose_name=_('Customer Responded')
    )
    response_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Response Date')
    )
    response_notes = models.TextField(
        blank=True,
        verbose_name=_('Response Notes')
    )
    
    # Gift suggestions (for birthdays/anniversaries)
    suggested_gifts = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Suggested Gifts'),
        help_text=_('List of suggested jewelry items for the occasion')
    )
    
    # Points awarded
    bonus_points_awarded = models.IntegerField(
        default=0,
        verbose_name=_('Bonus Points Awarded')
    )
    
    class Meta:
        verbose_name = _('Customer Engagement Event')
        verbose_name_plural = _('Customer Engagement Events')
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['customer', 'event_type']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.customer} - {self.get_event_type_display()} - {self.scheduled_date.date()}"
    
    def mark_as_sent(self):
        """Mark event as sent."""
        self.status = 'sent'
        self.sent_date = timezone.now()
        self.save(update_fields=['status', 'sent_date', 'updated_at'])
    
    def mark_as_delivered(self):
        """Mark event as delivered."""
        self.status = 'delivered'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_failed(self, reason=""):
        """Mark event as failed."""
        self.status = 'failed'
        if reason:
            self.response_notes = reason
        self.save(update_fields=['status', 'response_notes', 'updated_at'])
    
    def record_response(self, notes=""):
        """Record customer response."""
        self.is_responded = True
        self.response_date = timezone.now()
        if notes:
            self.response_notes = notes
        self.save(update_fields=['is_responded', 'response_date', 'response_notes', 'updated_at'])


class CustomerVIPTier(TenantAwareModel):
    """
    Track customer VIP tier history and benefits.
    """
    VIP_TIERS = [
        ('regular', _('Regular Customer')),
        ('bronze', _('Bronze VIP')),
        ('silver', _('Silver VIP')),
        ('gold', _('Gold VIP')),
        ('platinum', _('Platinum VIP')),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='vip_history',
        verbose_name=_('Customer')
    )
    loyalty_program = models.ForeignKey(
        CustomerLoyaltyProgram,
        on_delete=models.CASCADE,
        verbose_name=_('Loyalty Program')
    )
    
    # Tier information
    tier = models.CharField(
        max_length=20,
        choices=VIP_TIERS,
        verbose_name=_('VIP Tier')
    )
    previous_tier = models.CharField(
        max_length=20,
        choices=VIP_TIERS,
        blank=True,
        verbose_name=_('Previous Tier')
    )
    
    # Tier qualification
    total_purchases_at_upgrade = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Total Purchases at Upgrade (Toman)')
    )
    points_balance_at_upgrade = models.IntegerField(
        default=0,
        verbose_name=_('Points Balance at Upgrade')
    )
    
    # Tier validity
    effective_date = models.DateField(
        verbose_name=_('Effective Date')
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Expiry Date')
    )
    is_current = models.BooleanField(
        default=True,
        verbose_name=_('Is Current Tier')
    )
    
    # Benefits tracking
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_('Discount Percentage')
    )
    bonus_points_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.0,
        verbose_name=_('Bonus Points Multiplier')
    )
    
    # Usage tracking
    benefits_used_count = models.IntegerField(
        default=0,
        verbose_name=_('Benefits Used Count')
    )
    total_savings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Savings from Benefits (Toman)')
    )
    
    class Meta:
        verbose_name = _('Customer VIP Tier')
        verbose_name_plural = _('Customer VIP Tiers')
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['customer', 'is_current']),
            models.Index(fields=['tier']),
            models.Index(fields=['effective_date']),
        ]
    
    def __str__(self):
        return f"{self.customer} - {self.get_tier_display()}"
    
    @property
    def is_active(self):
        """Check if tier is currently active."""
        if not self.is_current:
            return False
        
        if self.expiry_date and self.expiry_date < timezone.now().date():
            return False
        
        return True
    
    def calculate_discount(self, amount):
        """Calculate discount amount for a purchase."""
        if not self.is_active:
            return 0
        
        return amount * (self.discount_percentage / 100)
    
    def calculate_bonus_points(self, base_points):
        """Calculate bonus points with tier multiplier."""
        if not self.is_active:
            return base_points
        
        return int(base_points * self.bonus_points_multiplier)
    
    def record_benefit_usage(self, savings_amount=0):
        """Record usage of VIP benefits."""
        self.benefits_used_count += 1
        self.total_savings += savings_amount
        self.save(update_fields=['benefits_used_count', 'total_savings', 'updated_at'])


class CustomerReferral(TenantAwareModel):
    """
    Track customer referrals for loyalty program.
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    
    referrer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='referrals_made',
        verbose_name=_('Referrer')
    )
    referred_customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='referrals_received',
        verbose_name=_('Referred Customer')
    )
    
    # Referral details
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Referral Code')
    )
    referral_date = models.DateField(
        verbose_name=_('Referral Date')
    )
    first_purchase_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('First Purchase Date')
    )
    
    # Status and rewards
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Status')
    )
    bonus_points_awarded = models.IntegerField(
        default=0,
        verbose_name=_('Bonus Points Awarded')
    )
    reward_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Reward Amount (Toman)')
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes')
    )
    
    class Meta:
        verbose_name = _('Customer Referral')
        verbose_name_plural = _('Customer Referrals')
        ordering = ['-referral_date']
        indexes = [
            models.Index(fields=['referrer']),
            models.Index(fields=['referral_code']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.referrer} → {self.referred_customer}"
    
    def complete_referral(self, purchase_amount=0):
        """Complete the referral when referred customer makes first purchase."""
        if self.status != 'pending':
            return False
        
        self.status = 'completed'
        self.first_purchase_date = timezone.now().date()
        
        # Award bonus points to referrer
        loyalty_program = CustomerLoyaltyProgram.objects.filter(
            tenant=self.referrer.tenant,
            is_active=True
        ).first()
        
        if loyalty_program:
            self.bonus_points_awarded = loyalty_program.referral_bonus_points
            self.referrer.add_loyalty_points(
                self.bonus_points_awarded,
                f"Referral bonus for {self.referred_customer.full_persian_name}"
            )
        
        self.save(update_fields=[
            'status', 
            'first_purchase_date', 
            'bonus_points_awarded',
            'updated_at'
        ])
        
        return True
    
    def generate_referral_code(self):
        """Generate unique referral code."""
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not CustomerReferral.objects.filter(referral_code=code).exists():
                return code


class CustomerSpecialOffer(TenantAwareModel):
    """
    Special offers and promotions for customers.
    """
    OFFER_TYPES = [
        ('birthday_discount', _('Birthday Discount')),
        ('anniversary_gift', _('Anniversary Gift')),
        ('vip_exclusive', _('VIP Exclusive Offer')),
        ('seasonal_promotion', _('Seasonal Promotion')),
        ('clearance_sale', _('Clearance Sale')),
        ('new_collection', _('New Collection Preview')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('used', _('Used')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='special_offers',
        verbose_name=_('Customer')
    )
    
    # Offer details
    offer_type = models.CharField(
        max_length=20,
        choices=OFFER_TYPES,
        verbose_name=_('Offer Type')
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_('Offer Title')
    )
    title_persian = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Persian Title')
    )
    description = models.TextField(
        verbose_name=_('Description')
    )
    description_persian = models.TextField(
        blank=True,
        verbose_name=_('Persian Description')
    )
    
    # Offer terms
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Discount Percentage')
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Discount Amount (Toman)')
    )
    minimum_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_('Minimum Purchase Amount (Toman)')
    )
    
    # Validity
    valid_from = models.DateTimeField(
        verbose_name=_('Valid From')
    )
    valid_until = models.DateTimeField(
        verbose_name=_('Valid Until')
    )
    max_uses = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_('Maximum Uses')
    )
    uses_count = models.IntegerField(
        default=0,
        verbose_name=_('Uses Count')
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Status')
    )
    
    # Usage tracking
    used_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Used Date')
    )
    used_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_('Used Amount (Toman)')
    )
    
    class Meta:
        verbose_name = _('Customer Special Offer')
        verbose_name_plural = _('Customer Special Offers')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['offer_type']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
    
    def __str__(self):
        return f"{self.customer} - {self.title_persian or self.title}"
    
    @property
    def is_valid(self):
        """Check if offer is currently valid."""
        now = timezone.now()
        return (
            self.status == 'active' and
            self.valid_from <= now <= self.valid_until and
            self.uses_count < self.max_uses
        )
    
    def calculate_discount(self, purchase_amount):
        """Calculate discount for a purchase amount."""
        if not self.is_valid or purchase_amount < self.minimum_purchase:
            return 0
        
        if self.discount_percentage > 0:
            return purchase_amount * (self.discount_percentage / 100)
        else:
            return min(self.discount_amount, purchase_amount)
    
    def use_offer(self, purchase_amount):
        """Use the offer for a purchase."""
        if not self.is_valid:
            return False
        
        discount = self.calculate_discount(purchase_amount)
        if discount <= 0:
            return False
        
        self.uses_count += 1
        self.used_amount += discount
        
        if self.uses_count >= self.max_uses:
            self.status = 'used'
            self.used_date = timezone.now()
        
        self.save(update_fields=[
            'uses_count', 
            'used_amount', 
            'status', 
            'used_date',
            'updated_at'
        ])
        
        return True