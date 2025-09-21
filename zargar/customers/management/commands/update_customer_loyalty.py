"""
Management command to update customer loyalty tiers and process loyalty program.
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count
from django_tenants.utils import get_tenant_model, tenant_context
from zargar.customers.models import Customer
from zargar.customers.loyalty_models import CustomerLoyaltyProgram, CustomerVIPTier
from zargar.customers.engagement_services import CustomerLoyaltyService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update customer loyalty tiers and process loyalty program benefits'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=int,
            help='Process only specific tenant (optional)'
        )
        parser.add_argument(
            '--customer-id',
            type=int,
            help='Process only specific customer (optional)'
        )
        parser.add_argument(
            '--recalculate-all',
            action='store_true',
            help='Recalculate tiers for all customers regardless of recent changes'
        )
        parser.add_argument(
            '--create-sample-program',
            action='store_true',
            help='Create sample loyalty program for tenants that don\'t have one'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it'
        )
    
    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        customer_id = options.get('customer_id')
        recalculate_all = options['recalculate_all']
        create_sample_program = options['create_sample_program']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Get tenants to process
        Tenant = get_tenant_model()
        if tenant_id:
            tenants = Tenant.objects.filter(id=tenant_id, is_active=True)
        else:
            tenants = Tenant.objects.filter(is_active=True)
        
        total_upgrades = 0
        total_programs_created = 0
        
        for tenant in tenants:
            with tenant_context(tenant):
                self.stdout.write(f"Processing tenant: {tenant.name}")
                
                loyalty_service = CustomerLoyaltyService(tenant)
                
                # Create sample loyalty program if requested and none exists
                if create_sample_program:
                    existing_program = loyalty_service.get_active_loyalty_program()
                    if not existing_program:
                        if not dry_run:
                            program = self._create_sample_loyalty_program(tenant)
                            total_programs_created += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"  Created sample loyalty program: {program.name_persian}")
                            )
                        else:
                            self.stdout.write("  Would create sample loyalty program")
                
                # Get customers to process
                if customer_id:
                    customers = Customer.objects.filter(id=customer_id, is_active=True)
                else:
                    customers = Customer.objects.filter(is_active=True)
                    
                    # If not recalculating all, only process customers with recent purchases
                    if not recalculate_all:
                        from django.utils import timezone
                        from datetime import timedelta
                        recent_date = timezone.now() - timedelta(days=30)
                        customers = customers.filter(last_purchase_date__gte=recent_date)
                
                upgrades_count = 0
                
                for customer in customers:
                    try:
                        if not dry_run:
                            # Update customer tier
                            tier_upgrade = loyalty_service.update_customer_tier(customer)
                            
                            if tier_upgrade:
                                upgrades_count += 1
                                self.stdout.write(
                                    f"    Upgraded {customer.full_persian_name} to {tier_upgrade.tier}"
                                )
                        else:
                            # Calculate what tier they should have
                            current_tier = loyalty_service.calculate_customer_tier(customer)
                            
                            # Get their actual current tier
                            actual_tier_record = CustomerVIPTier.objects.filter(
                                customer=customer,
                                is_current=True
                            ).first()
                            actual_tier = actual_tier_record.tier if actual_tier_record else 'regular'
                            
                            if current_tier != actual_tier:
                                self.stdout.write(
                                    f"    Would upgrade {customer.full_persian_name} "
                                    f"from {actual_tier} to {current_tier}"
                                )
                    
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"    Error processing customer {customer.id}: {e}"
                            )
                        )
                        logger.error(f"Error processing customer {customer.id}: {e}")
                
                if not dry_run:
                    total_upgrades += upgrades_count
                    self.stdout.write(
                        self.style.SUCCESS(f"  Processed {customers.count()} customers, {upgrades_count} upgrades")
                    )
                
                # Display loyalty program statistics
                self._display_loyalty_statistics(tenant, loyalty_service)
        
        # Summary
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSummary:\n"
                    f"  Total tier upgrades: {total_upgrades}\n"
                    f"  Total programs created: {total_programs_created}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN completed. Use --no-dry-run to execute changes."
                )
            )
    
    def _create_sample_loyalty_program(self, tenant) -> CustomerLoyaltyProgram:
        """Create a sample loyalty program for the tenant."""
        from django.utils import timezone
        
        program = CustomerLoyaltyProgram.objects.create(
            tenant=tenant,
            name="Default Loyalty Program",
            name_persian="برنامه وفاداری پیش‌فرض",
            description="Earn points with every purchase and enjoy VIP benefits",
            description_persian="با هر خرید امتیاز کسب کنید و از مزایای VIP بهره‌مند شوید",
            program_type='hybrid',
            start_date=timezone.now().date(),
            points_per_toman=0.1,  # 1 point per 10 Toman
            toman_per_point=10.0,  # Each point worth 10 Toman
            vip_threshold_bronze=10000000,   # 10 million Toman
            vip_threshold_silver=25000000,   # 25 million Toman
            vip_threshold_gold=50000000,     # 50 million Toman
            vip_threshold_platinum=100000000, # 100 million Toman
            birthday_bonus_points=1000,
            anniversary_bonus_points=500,
            nowruz_bonus_points=2000,
            yalda_bonus_points=1500,
            wedding_bonus_points=3000,
            referral_bonus_points=2000,
            points_expire_months=24
        )
        
        return program
    
    def _display_loyalty_statistics(self, tenant, loyalty_service: CustomerLoyaltyService):
        """Display loyalty program statistics for the tenant."""
        
        program = loyalty_service.get_active_loyalty_program()
        if not program:
            self.stdout.write("  No active loyalty program")
            return
        
        # Get tier distribution
        tier_stats = CustomerVIPTier.objects.filter(
            customer__tenant=tenant,
            is_current=True
        ).values('tier').annotate(count=Count('id'))
        
        # Get total customers
        total_customers = Customer.objects.filter(tenant=tenant, is_active=True).count()
        
        # Get customers with points
        customers_with_points = Customer.objects.filter(
            tenant=tenant,
            is_active=True,
            loyalty_points__gt=0
        ).count()
        
        # Get total points issued
        total_points = Customer.objects.filter(
            tenant=tenant,
            is_active=True
        ).aggregate(total=Sum('loyalty_points'))['total'] or 0
        
        self.stdout.write(f"  Loyalty Program Statistics:")
        self.stdout.write(f"    Program: {program.name_persian}")
        self.stdout.write(f"    Total customers: {total_customers}")
        self.stdout.write(f"    Customers with points: {customers_with_points}")
        self.stdout.write(f"    Total points issued: {total_points:,}")
        
        self.stdout.write(f"    VIP Tier Distribution:")
        tier_names = {
            'regular': 'عادی',
            'bronze': 'برنز',
            'silver': 'نقره‌ای',
            'gold': 'طلایی',
            'platinum': 'پلاتینیوم'
        }
        
        for tier_stat in tier_stats:
            tier_name = tier_names.get(tier_stat['tier'], tier_stat['tier'])
            self.stdout.write(f"      {tier_name}: {tier_stat['count']} customers")
        
        # Count regular customers (those without VIP tier records)
        vip_customers_count = sum(stat['count'] for stat in tier_stats)
        regular_customers_count = total_customers - vip_customers_count
        if regular_customers_count > 0:
            self.stdout.write(f"      عادی: {regular_customers_count} customers")