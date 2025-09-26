"""
Gold installment services for ZARGAR jewelry SaaS platform.
Provides gold price integration and payment processing logic.
"""
import requests
from typing import Dict, Optional, Tuple, List
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
import logging

from .models import GoldInstallmentContract, GoldInstallmentPayment, GoldWeightAdjustment
from zargar.core.external_services import IranianGoldPriceAPI

logger = logging.getLogger(__name__)


class GoldPriceService:
    """
    Service for fetching and managing gold prices from Iranian market APIs.
    Provides real-time gold price integration with caching and fallback mechanisms.
    
    This class now delegates to the enhanced IranianGoldPriceAPI for better integration.
    """
    
    # Maintain backward compatibility
    CACHE_KEY_PREFIX = IranianGoldPriceAPI.CACHE_KEY_PREFIX
    CACHE_TIMEOUT = IranianGoldPriceAPI.CACHE_TIMEOUT
    GOLD_PRICE_APIS = IranianGoldPriceAPI.GOLD_PRICE_APIS
    
    @classmethod
    def get_current_gold_price(cls, karat: int = 18) -> Dict[str, Decimal]:
        """
        Get current gold price for specified karat using enhanced Iranian API integration.
        
        Args:
            karat: Gold karat (default 18)
            
        Returns:
            Dictionary with price information
        """
        # Use the enhanced Iranian Gold Price API
        price_data = IranianGoldPriceAPI.get_current_gold_price(karat)
        
        # Convert to expected format for backward compatibility
        return {
            'price_per_gram': price_data['price_per_gram'],
            'karat': price_data['karat'],
            'timestamp': price_data['timestamp'],
            'source': price_data['source'],
            'currency': 'TMN'  # Toman for Iranian market
        }
    
    @classmethod
    def get_price_trend(cls, karat: int = 18, days: int = 30) -> List[Dict]:
        """
        Get gold price trend for specified period using enhanced Iranian API.
        
        Args:
            karat: Gold karat
            days: Number of days for trend analysis
            
        Returns:
            List of price data points
        """
        return IranianGoldPriceAPI.get_price_trend(karat, days)
    
    @classmethod
    def invalidate_cache(cls, karat: Optional[int] = None):
        """
        Invalidate gold price cache using enhanced Iranian API.
        
        Args:
            karat: Specific karat to invalidate, or None for all
        """
        IranianGoldPriceAPI.invalidate_cache(karat)


class PaymentProcessingService:
    """
    Service for processing gold installment payments with price protection and discounts.
    Handles bidirectional transactions and complex payment calculations.
    """
    
    @classmethod
    def process_payment(cls, contract: GoldInstallmentContract, 
                       payment_amount: Decimal,
                       payment_method: str = 'cash',
                       payment_date: Optional[datetime] = None,
                       apply_early_discount: bool = False,
                       notes: str = '') -> Dict:
        """
        Process a payment for gold installment contract.
        
        Args:
            contract: GoldInstallmentContract instance
            payment_amount: Payment amount in Toman
            payment_method: Payment method
            payment_date: Payment date (defaults to now)
            apply_early_discount: Whether to apply early payment discount
            notes: Payment notes
            
        Returns:
            Dictionary with payment processing results
        """
        if payment_date is None:
            payment_date = timezone.now().date()
        
        # Validate contract status
        if contract.status not in ['active', 'suspended']:
            raise ValidationError(f"Cannot process payment for contract with status: {contract.status}")
        
        # Get current gold price
        gold_price_data = GoldPriceService.get_current_gold_price(contract.gold_karat)
        market_price = gold_price_data['price_per_gram']
        
        # Apply price protection
        effective_price = cls._apply_price_protection(contract, market_price)
        
        # Calculate payment details
        payment_details = cls._calculate_payment_details(
            contract, payment_amount, effective_price, apply_early_discount
        )
        
        try:
            with transaction.atomic():
                # Create payment record
                payment = GoldInstallmentPayment.objects.create(
                    contract=contract,
                    payment_date=payment_date,
                    payment_amount_toman=payment_amount,
                    gold_price_per_gram_at_payment=market_price,
                    effective_gold_price_per_gram=effective_price,
                    gold_weight_equivalent_grams=payment_details['gold_weight_equivalent'],
                    payment_method=payment_method,
                    payment_type='early_completion' if apply_early_discount else 'regular',
                    discount_applied=payment_details['discount_applied'],
                    discount_percentage=payment_details['discount_percentage'],
                    discount_amount_toman=payment_details['discount_amount'],
                    payment_notes=notes
                )
                
                # Update contract balance
                cls._update_contract_balance(contract, payment_details)
                
                # Log the transaction
                logger.info(f"Processed payment for contract {contract.contract_number}: "
                           f"{payment_amount} Toman = {payment_details['gold_weight_equivalent']} grams")
                
                return {
                    'success': True,
                    'payment': payment,
                    'payment_details': payment_details,
                    'contract_updated': True,
                    'remaining_balance': contract.remaining_gold_weight_grams
                }
                
        except Exception as e:
            logger.error(f"Error processing payment for contract {contract.contract_number}: {e}")
            raise ValidationError(f"Payment processing failed: {str(e)}")
    
    @classmethod
    def _apply_price_protection(cls, contract: GoldInstallmentContract, 
                               market_price: Decimal) -> Decimal:
        """
        Apply price protection (ceiling/floor) to market price.
        
        Args:
            contract: GoldInstallmentContract instance
            market_price: Current market price
            
        Returns:
            Effective price after protection
        """
        if not contract.has_price_protection:
            return market_price
        
        effective_price = market_price
        
        # Apply ceiling protection
        if (contract.price_ceiling_per_gram and 
            market_price > contract.price_ceiling_per_gram):
            effective_price = contract.price_ceiling_per_gram
            logger.info(f"Applied price ceiling for contract {contract.contract_number}: "
                       f"{market_price} -> {effective_price}")
        
        # Apply floor protection
        elif (contract.price_floor_per_gram and 
              market_price < contract.price_floor_per_gram):
            effective_price = contract.price_floor_per_gram
            logger.info(f"Applied price floor for contract {contract.contract_number}: "
                       f"{market_price} -> {effective_price}")
        
        return effective_price
    
    @classmethod
    def _calculate_payment_details(cls, contract: GoldInstallmentContract,
                                  payment_amount: Decimal,
                                  effective_price: Decimal,
                                  apply_early_discount: bool) -> Dict:
        """
        Calculate detailed payment information including discounts.
        
        Args:
            contract: GoldInstallmentContract instance
            payment_amount: Payment amount in Toman
            effective_price: Effective gold price per gram
            apply_early_discount: Whether to apply early payment discount
            
        Returns:
            Dictionary with payment calculation details
        """
        # Basic gold weight calculation
        gold_weight_equivalent = (payment_amount / effective_price).quantize(
            Decimal('0.001'), rounding=ROUND_HALF_UP
        )
        
        # Initialize discount values
        discount_applied = False
        discount_percentage = Decimal('0.00')
        discount_amount = Decimal('0.00')
        
        # Apply early payment discount if requested and eligible
        if (apply_early_discount and 
            contract.early_payment_discount_percentage > 0 and
            contract.status == 'active'):
            
            # Check if this payment would complete the contract
            remaining_value = contract.remaining_gold_weight_grams * effective_price
            
            if payment_amount >= remaining_value:
                discount_percentage = contract.early_payment_discount_percentage
                discount_amount = remaining_value * (discount_percentage / 100)
                
                # Adjust payment amount and gold weight
                discounted_payment = payment_amount - discount_amount
                gold_weight_equivalent = (discounted_payment / effective_price).quantize(
                    Decimal('0.001'), rounding=ROUND_HALF_UP
                )
                
                discount_applied = True
                logger.info(f"Applied early payment discount for contract {contract.contract_number}: "
                           f"{discount_percentage}% = {discount_amount} Toman")
        
        return {
            'gold_weight_equivalent': gold_weight_equivalent,
            'discount_applied': discount_applied,
            'discount_percentage': discount_percentage,
            'discount_amount': discount_amount,
            'effective_price_used': effective_price
        }
    
    @classmethod
    def _update_contract_balance(cls, contract: GoldInstallmentContract, 
                                payment_details: Dict):
        """
        Update contract balance after payment processing.
        
        Args:
            contract: GoldInstallmentContract instance
            payment_details: Payment calculation details
        """
        # Update remaining weight
        contract.remaining_gold_weight_grams -= payment_details['gold_weight_equivalent']
        contract.total_gold_weight_paid += payment_details['gold_weight_equivalent']
        
        # Ensure remaining weight doesn't go negative
        if contract.remaining_gold_weight_grams < Decimal('0.000'):
            contract.remaining_gold_weight_grams = Decimal('0.000')
        
        # Check if contract is completed
        if contract.remaining_gold_weight_grams <= Decimal('0.001'):
            contract.status = 'completed'
            contract.completion_date = timezone.now().date()
            logger.info(f"Contract {contract.contract_number} marked as completed")
        
        contract.save(update_fields=[
            'remaining_gold_weight_grams',
            'total_gold_weight_paid',
            'status',
            'completion_date',
            'updated_at'
        ])
    
    @classmethod
    def process_bidirectional_transaction(cls, contract: GoldInstallmentContract,
                                        transaction_type: str,
                                        amount: Decimal,
                                        description: str,
                                        authorized_by) -> Dict:
        """
        Process bidirectional transactions (debt/credit adjustments).
        
        Args:
            contract: GoldInstallmentContract instance
            transaction_type: 'debt' or 'credit'
            amount: Transaction amount in gold weight (grams)
            description: Transaction description
            authorized_by: User authorizing the transaction
            
        Returns:
            Dictionary with transaction results
        """
        if transaction_type not in ['debt', 'credit']:
            raise ValidationError("Transaction type must be 'debt' or 'credit'")
        
        try:
            with transaction.atomic():
                # Create weight adjustment record
                adjustment_amount = amount if transaction_type == 'debt' else -amount
                
                adjustment = GoldWeightAdjustment.objects.create(
                    contract=contract,
                    adjustment_date=timezone.now().date(),
                    weight_before_grams=contract.remaining_gold_weight_grams,
                    adjustment_amount_grams=adjustment_amount,
                    adjustment_type='increase' if transaction_type == 'debt' else 'decrease',
                    adjustment_reason='other',
                    description=description,
                    authorized_by=authorized_by
                )
                
                # Update contract balance type if needed
                if transaction_type == 'credit' and contract.balance_type == 'debt':
                    if contract.remaining_gold_weight_grams <= amount:
                        contract.balance_type = 'credit'
                        contract.remaining_gold_weight_grams = amount - contract.remaining_gold_weight_grams
                elif transaction_type == 'debt' and contract.balance_type == 'credit':
                    if contract.remaining_gold_weight_grams <= amount:
                        contract.balance_type = 'debt'
                        contract.remaining_gold_weight_grams = amount - contract.remaining_gold_weight_grams
                
                contract.save(update_fields=['balance_type', 'updated_at'])
                
                logger.info(f"Processed {transaction_type} transaction for contract "
                           f"{contract.contract_number}: {amount} grams")
                
                return {
                    'success': True,
                    'adjustment': adjustment,
                    'new_balance': contract.remaining_gold_weight_grams,
                    'balance_type': contract.balance_type
                }
                
        except Exception as e:
            logger.error(f"Error processing bidirectional transaction: {e}")
            raise ValidationError(f"Transaction processing failed: {str(e)}")
    
    @classmethod
    def calculate_early_payment_savings(cls, contract: GoldInstallmentContract) -> Dict:
        """
        Calculate potential savings from early payment completion.
        
        Args:
            contract: GoldInstallmentContract instance
            
        Returns:
            Dictionary with savings calculation
        """
        if contract.early_payment_discount_percentage <= 0:
            return {
                'eligible': False,
                'discount_percentage': Decimal('0.00'),
                'current_balance_value': Decimal('0.00'),
                'discount_amount': Decimal('0.00'),
                'final_payment_amount': Decimal('0.00'),
                'savings': Decimal('0.00')
            }
        
        # Get current gold price
        gold_price_data = GoldPriceService.get_current_gold_price(contract.gold_karat)
        effective_price = cls._apply_price_protection(contract, gold_price_data['price_per_gram'])
        
        # Calculate current balance value
        current_balance_value = contract.remaining_gold_weight_grams * effective_price
        
        # Calculate discount
        discount_amount = current_balance_value * (contract.early_payment_discount_percentage / 100)
        final_payment_amount = current_balance_value - discount_amount
        
        return {
            'eligible': True,
            'discount_percentage': contract.early_payment_discount_percentage,
            'current_balance_value': current_balance_value,
            'discount_amount': discount_amount,
            'final_payment_amount': final_payment_amount,
            'savings': discount_amount,
            'effective_gold_price': effective_price
        }


class GoldPriceProtectionService:
    """
    Service for managing gold price protection features.
    Handles ceiling/floor price protection and related calculations.
    """
    
    @classmethod
    def setup_price_protection(cls, contract: GoldInstallmentContract,
                              ceiling_price: Optional[Decimal] = None,
                              floor_price: Optional[Decimal] = None) -> Dict:
        """
        Set up price protection for a contract.
        
        Args:
            contract: GoldInstallmentContract instance
            ceiling_price: Maximum price per gram
            floor_price: Minimum price per gram
            
        Returns:
            Dictionary with setup results
        """
        if not ceiling_price and not floor_price:
            raise ValidationError("At least one of ceiling or floor price must be provided")
        
        if ceiling_price and floor_price and ceiling_price <= floor_price:
            raise ValidationError("Ceiling price must be higher than floor price")
        
        # Update contract
        contract.has_price_protection = True
        contract.price_ceiling_per_gram = ceiling_price
        contract.price_floor_per_gram = floor_price
        contract.save(update_fields=[
            'has_price_protection',
            'price_ceiling_per_gram', 
            'price_floor_per_gram',
            'updated_at'
        ])
        
        logger.info(f"Set up price protection for contract {contract.contract_number}: "
                   f"ceiling={ceiling_price}, floor={floor_price}")
        
        return {
            'success': True,
            'ceiling_price': ceiling_price,
            'floor_price': floor_price,
            'protection_active': True
        }
    
    @classmethod
    def remove_price_protection(cls, contract: GoldInstallmentContract) -> Dict:
        """
        Remove price protection from a contract.
        
        Args:
            contract: GoldInstallmentContract instance
            
        Returns:
            Dictionary with removal results
        """
        contract.has_price_protection = False
        contract.price_ceiling_per_gram = None
        contract.price_floor_per_gram = None
        contract.save(update_fields=[
            'has_price_protection',
            'price_ceiling_per_gram',
            'price_floor_per_gram',
            'updated_at'
        ])
        
        logger.info(f"Removed price protection for contract {contract.contract_number}")
        
        return {
            'success': True,
            'protection_active': False
        }
    
    @classmethod
    def analyze_price_protection_impact(cls, contract: GoldInstallmentContract) -> Dict:
        """
        Analyze the impact of price protection on contract payments.
        
        Args:
            contract: GoldInstallmentContract instance
            
        Returns:
            Dictionary with impact analysis
        """
        if not contract.has_price_protection:
            return {
                'has_protection': False,
                'impact_analysis': None
            }
        
        # Get current market price
        gold_price_data = GoldPriceService.get_current_gold_price(contract.gold_karat)
        market_price = gold_price_data['price_per_gram']
        
        # Determine effective price
        effective_price = market_price
        protection_type = None
        
        if (contract.price_ceiling_per_gram and 
            market_price > contract.price_ceiling_per_gram):
            effective_price = contract.price_ceiling_per_gram
            protection_type = 'ceiling'
        elif (contract.price_floor_per_gram and 
              market_price < contract.price_floor_per_gram):
            effective_price = contract.price_floor_per_gram
            protection_type = 'floor'
        
        # Calculate impact
        protection_active = protection_type is not None
        price_difference = market_price - effective_price if protection_active else Decimal('0.00')
        
        # Calculate value impact on remaining balance
        remaining_value_market = contract.remaining_gold_weight_grams * market_price
        remaining_value_protected = contract.remaining_gold_weight_grams * effective_price
        value_impact = remaining_value_market - remaining_value_protected
        
        return {
            'has_protection': True,
            'protection_active': protection_active,
            'protection_type': protection_type,
            'market_price': market_price,
            'effective_price': effective_price,
            'price_difference': price_difference,
            'ceiling_price': contract.price_ceiling_per_gram,
            'floor_price': contract.price_floor_per_gram,
            'remaining_value_market': remaining_value_market,
            'remaining_value_protected': remaining_value_protected,
            'value_impact': value_impact,
            'customer_benefit': value_impact > 0  # Positive means customer benefits
        }