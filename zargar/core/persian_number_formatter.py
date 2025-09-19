"""
Persian number formatting and currency system for ZARGAR jewelry SaaS platform.
Provides comprehensive formatting for Toman currency, Persian numerals, and weight conversions.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Union, Optional, Dict, Tuple
import re


class PersianNumberFormatter:
    """
    Comprehensive Persian number formatting system with currency and weight conversion support.
    """
    
    # Persian digit mapping
    ENGLISH_DIGITS = '0123456789'
    PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
    
    # Persian number names for large numbers
    PERSIAN_NUMBER_NAMES = {
        1: '',
        1000: 'هزار',
        1000000: 'میلیون',
        1000000000: 'میلیارد',
        1000000000000: 'بیلیون',
        1000000000000000: 'بیلیارد'
    }
    
    # Traditional Persian weight units
    WEIGHT_UNITS = {
        'gram': {'name': 'گرم', 'symbol': 'گ', 'to_gram': 1},
        'mesghal': {'name': 'مثقال', 'symbol': 'م', 'to_gram': 4.608},  # Traditional Persian unit
        'soot': {'name': 'سوت', 'symbol': 'س', 'to_gram': 0.2304},      # 1/20 of mesghal
        'dirham': {'name': 'درهم', 'symbol': 'د', 'to_gram': 3.125},    # Traditional unit
        'ounce': {'name': 'اونس', 'symbol': 'او', 'to_gram': 28.3495},   # Troy ounce
        'tola': {'name': 'تولا', 'symbol': 'ت', 'to_gram': 11.6638}      # Used in some regions
    }
    
    @classmethod
    def to_persian_digits(cls, text: Union[str, int, float, Decimal]) -> str:
        """
        Convert English digits to Persian digits.
        
        Args:
            text: Text, number, or decimal containing English digits
            
        Returns:
            Text with Persian digits
        """
        text_str = str(text)
        
        for i, digit in enumerate(cls.ENGLISH_DIGITS):
            text_str = text_str.replace(digit, cls.PERSIAN_DIGITS[i])
        
        return text_str
    
    @classmethod
    def to_english_digits(cls, text: str) -> str:
        """
        Convert Persian digits to English digits.
        
        Args:
            text: Text containing Persian digits
            
        Returns:
            Text with English digits
        """
        for i, digit in enumerate(cls.PERSIAN_DIGITS):
            text = text.replace(digit, cls.ENGLISH_DIGITS[i])
        
        return text
    
    @classmethod
    def format_currency(cls, amount: Union[int, float, Decimal], 
                       include_symbol: bool = True,
                       use_persian_digits: bool = True,
                       show_decimals: bool = False,
                       decimal_places: int = 0) -> str:
        """
        Format currency in Iranian Toman with Persian numerals.
        
        Args:
            amount: Amount in Toman
            include_symbol: Whether to include Toman symbol
            use_persian_digits: Whether to use Persian numerals
            show_decimals: Whether to show decimal places
            decimal_places: Number of decimal places (0-2)
            
        Returns:
            Formatted currency string
        """
        if amount is None:
            return '۰ تومان' if use_persian_digits else '0 تومان'
        
        # Convert to Decimal for precise calculations
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        # Round to specified decimal places
        if decimal_places > 0 and show_decimals:
            amount = amount.quantize(Decimal('0.' + '0' * decimal_places), rounding=ROUND_HALF_UP)
        else:
            amount = amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # Format with thousand separators
        if show_decimals and decimal_places > 0:
            formatted = f"{amount:,.{decimal_places}f}"
        else:
            formatted = f"{int(amount):,}"
        
        # Convert to Persian digits if requested
        if use_persian_digits:
            formatted = cls.to_persian_digits(formatted)
            # Replace comma with Persian thousands separator
            formatted = formatted.replace(',', '،')
        
        # Add currency symbol
        if include_symbol:
            formatted += ' تومان'
        
        return formatted
    
    @classmethod
    def format_large_number(cls, number: Union[int, float, Decimal],
                          use_persian_digits: bool = True,
                          use_word_format: bool = False) -> str:
        """
        Format large numbers with Iranian number formatting standards.
        
        Args:
            number: Number to format
            use_persian_digits: Whether to use Persian numerals
            use_word_format: Whether to use word format (e.g., "۱۰ میلیون")
            
        Returns:
            Formatted number string
        """
        if number is None:
            return '۰' if use_persian_digits else '0'
        
        # Convert to Decimal for precise calculations
        if not isinstance(number, Decimal):
            number = Decimal(str(number))
        
        # Handle negative numbers
        is_negative = number < 0
        number = abs(number)
        
        if use_word_format and number >= 1000:
            formatted = cls._format_number_with_words(number, use_persian_digits)
        else:
            # Standard formatting with thousand separators
            formatted = f"{int(number):,}"
            
            if use_persian_digits:
                formatted = cls.to_persian_digits(formatted)
                # Replace comma with Persian thousands separator
                formatted = formatted.replace(',', '،')
        
        # Add negative sign if needed
        if is_negative:
            formatted = f"-{formatted}"
        
        return formatted
    
    @classmethod
    def _format_number_with_words(cls, number: Decimal, use_persian_digits: bool) -> str:
        """
        Format number with Persian word units (میلیون، میلیارد، etc.).
        
        Args:
            number: Number to format
            use_persian_digits: Whether to use Persian digits
            
        Returns:
            Formatted number with words
        """
        # Find the largest unit that fits
        for unit_value in sorted(cls.PERSIAN_NUMBER_NAMES.keys(), reverse=True):
            if number >= unit_value and unit_value > 1:
                quotient = number / unit_value
                remainder = number % unit_value
                
                # Format the quotient
                if quotient >= 1000:
                    # Recursively format large quotients
                    quotient_str = cls._format_number_with_words(quotient, use_persian_digits)
                else:
                    quotient_str = f"{int(quotient):,}"
                    if use_persian_digits:
                        quotient_str = cls.to_persian_digits(quotient_str)
                        quotient_str = quotient_str.replace(',', '،')
                
                unit_name = cls.PERSIAN_NUMBER_NAMES[unit_value]
                result = f"{quotient_str} {unit_name}"
                
                # Add remainder if significant
                if remainder >= 1000:
                    remainder_str = cls._format_number_with_words(remainder, use_persian_digits)
                    result += f" و {remainder_str}"
                elif remainder > 0:
                    remainder_str = f"{int(remainder):,}"
                    if use_persian_digits:
                        remainder_str = cls.to_persian_digits(remainder_str)
                        remainder_str = remainder_str.replace(',', '،')
                    result += f" و {remainder_str}"
                
                return result
        
        # For numbers less than 1000
        formatted = f"{int(number):,}"
        if use_persian_digits:
            formatted = cls.to_persian_digits(formatted)
            formatted = formatted.replace(',', '،')
        
        return formatted
    
    @classmethod
    def convert_weight(cls, weight: Union[int, float, Decimal], 
                      from_unit: str, to_unit: str,
                      precision: int = 3) -> Decimal:
        """
        Convert between different weight units.
        
        Args:
            weight: Weight value to convert
            from_unit: Source unit (gram, mesghal, soot, etc.)
            to_unit: Target unit
            precision: Decimal precision for result
            
        Returns:
            Converted weight as Decimal
            
        Raises:
            ValueError: If units are not supported
        """
        if from_unit not in cls.WEIGHT_UNITS:
            raise ValueError(f"Unsupported source unit: {from_unit}")
        
        if to_unit not in cls.WEIGHT_UNITS:
            raise ValueError(f"Unsupported target unit: {to_unit}")
        
        # Convert to Decimal for precise calculations
        if not isinstance(weight, Decimal):
            weight = Decimal(str(weight))
        
        # Convert to grams first, then to target unit
        weight_in_grams = weight * Decimal(str(cls.WEIGHT_UNITS[from_unit]['to_gram']))
        converted_weight = weight_in_grams / Decimal(str(cls.WEIGHT_UNITS[to_unit]['to_gram']))
        
        # Round to specified precision
        precision_str = '0.' + '0' * precision
        return converted_weight.quantize(Decimal(precision_str), rounding=ROUND_HALF_UP)
    
    @classmethod
    def format_weight(cls, weight: Union[int, float, Decimal], 
                     unit: str = 'gram',
                     use_persian_digits: bool = True,
                     show_unit_name: bool = True,
                     precision: int = 3) -> str:
        """
        Format weight with Persian units.
        
        Args:
            weight: Weight value
            unit: Weight unit (gram, mesghal, soot, etc.)
            use_persian_digits: Whether to use Persian numerals
            show_unit_name: Whether to show unit name
            precision: Decimal precision
            
        Returns:
            Formatted weight string
        """
        if weight is None:
            return '۰ گرم' if use_persian_digits else '0 gram'
        
        if unit not in cls.WEIGHT_UNITS:
            raise ValueError(f"Unsupported weight unit: {unit}")
        
        # Convert to Decimal for precise calculations
        if not isinstance(weight, Decimal):
            weight = Decimal(str(weight))
        
        # Round to specified precision
        precision_str = '0.' + '0' * precision
        weight = weight.quantize(Decimal(precision_str), rounding=ROUND_HALF_UP)
        
        # Format the number - remove trailing zeros for cleaner display
        if weight == int(weight):
            # Show as integer if no decimal part
            formatted = f"{int(weight):,}"
        else:
            # Format with decimals but remove trailing zeros
            formatted = f"{weight:,}".rstrip('0').rstrip('.')
        
        # Convert to Persian digits if requested
        if use_persian_digits:
            formatted = cls.to_persian_digits(formatted)
            formatted = formatted.replace(',', '،')
        
        # Add unit name or symbol
        if show_unit_name:
            unit_info = cls.WEIGHT_UNITS[unit]
            formatted += f" {unit_info['name']}"
        
        return formatted
    
    @classmethod
    def format_weight_with_conversion(cls, weight_grams: Union[int, float, Decimal],
                                    target_units: Optional[list] = None,
                                    use_persian_digits: bool = True) -> Dict[str, str]:
        """
        Format weight in multiple units for display.
        
        Args:
            weight_grams: Weight in grams
            target_units: List of units to convert to, defaults to common units
            use_persian_digits: Whether to use Persian numerals
            
        Returns:
            Dictionary mapping unit names to formatted strings
        """
        if target_units is None:
            target_units = ['gram', 'mesghal', 'soot']
        
        if weight_grams is None:
            return {unit: '۰' if use_persian_digits else '0' for unit in target_units}
        
        results = {}
        
        for unit in target_units:
            if unit in cls.WEIGHT_UNITS:
                converted_weight = cls.convert_weight(weight_grams, 'gram', unit)
                formatted = cls.format_weight(converted_weight, unit, use_persian_digits)
                results[unit] = formatted
        
        return results
    
    @classmethod
    def parse_persian_number(cls, text: str) -> Optional[Decimal]:
        """
        Parse Persian number string to Decimal.
        
        Args:
            text: Persian number string
            
        Returns:
            Decimal value or None if parsing fails
        """
        if not text or not isinstance(text, str):
            return None
        
        # Clean the text
        text = text.strip()
        
        # Convert Persian digits to English
        text = cls.to_english_digits(text)
        
        # Remove Persian thousands separators
        text = text.replace('،', '')
        
        # Remove regular commas
        text = text.replace(',', '')
        
        # Remove currency symbols
        text = text.replace('تومان', '').replace('ریال', '').strip()
        
        # Remove weight unit names
        for unit_info in cls.WEIGHT_UNITS.values():
            text = text.replace(unit_info['name'], '').replace(unit_info['symbol'], '').strip()
        
        # Final validation - check if remaining text is a valid number
        if not text or not re.match(r'^-?\d*\.?\d*$', text):
            return None
        
        try:
            return Decimal(text)
        except (ValueError, TypeError, Exception):
            return None
    
    @classmethod
    def format_percentage(cls, percentage: Union[int, float, Decimal],
                         use_persian_digits: bool = True,
                         decimal_places: int = 1) -> str:
        """
        Format percentage with Persian digits.
        
        Args:
            percentage: Percentage value (0-100)
            use_persian_digits: Whether to use Persian numerals
            decimal_places: Number of decimal places
            
        Returns:
            Formatted percentage string
        """
        if percentage is None:
            return '۰٪' if use_persian_digits else '0%'
        
        # Convert to Decimal for precise calculations
        if not isinstance(percentage, Decimal):
            percentage = Decimal(str(percentage))
        
        # Round to specified decimal places
        if decimal_places > 0:
            precision_str = '0.' + '0' * decimal_places
            percentage = percentage.quantize(Decimal(precision_str), rounding=ROUND_HALF_UP)
            formatted = f"{percentage:.{decimal_places}f}"
        else:
            percentage = percentage.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            formatted = f"{int(percentage)}"
        
        # Convert to Persian digits if requested
        if use_persian_digits:
            formatted = cls.to_persian_digits(formatted)
            formatted += '٪'  # Persian percent sign
        else:
            formatted += '%'
        
        return formatted
    
    @classmethod
    def format_gold_price(cls, price_per_gram: Union[int, float, Decimal],
                         weight_grams: Union[int, float, Decimal],
                         use_persian_digits: bool = True) -> Dict[str, str]:
        """
        Format gold price calculations for jewelry.
        
        Args:
            price_per_gram: Gold price per gram in Toman
            weight_grams: Weight in grams
            use_persian_digits: Whether to use Persian numerals
            
        Returns:
            Dictionary with formatted price information
        """
        if price_per_gram is None or weight_grams is None:
            empty_value = '۰ تومان' if use_persian_digits else '0 Toman'
            return {
                'price_per_gram': empty_value,
                'total_value': empty_value,
                'weight_display': '۰ گرم' if use_persian_digits else '0 gram'
            }
        
        # Convert to Decimal for precise calculations
        if not isinstance(price_per_gram, Decimal):
            price_per_gram = Decimal(str(price_per_gram))
        
        if not isinstance(weight_grams, Decimal):
            weight_grams = Decimal(str(weight_grams))
        
        # Calculate total value
        total_value = price_per_gram * weight_grams
        
        return {
            'price_per_gram': cls.format_currency(price_per_gram, use_persian_digits=use_persian_digits),
            'total_value': cls.format_currency(total_value, use_persian_digits=use_persian_digits),
            'weight_display': cls.format_weight(weight_grams, 'gram', use_persian_digits=use_persian_digits),
            'weight_mesghal': cls.format_weight(
                cls.convert_weight(weight_grams, 'gram', 'mesghal'), 
                'mesghal', 
                use_persian_digits=use_persian_digits
            ),
            'weight_soot': cls.format_weight(
                cls.convert_weight(weight_grams, 'gram', 'soot'), 
                'soot', 
                use_persian_digits=use_persian_digits
            )
        }
    
    @classmethod
    def get_supported_weight_units(cls) -> Dict[str, Dict[str, Union[str, float]]]:
        """
        Get all supported weight units with their information.
        
        Returns:
            Dictionary of weight units with their details
        """
        return cls.WEIGHT_UNITS.copy()
    
    @classmethod
    def validate_currency_input(cls, input_text: str) -> Tuple[bool, Optional[Decimal], str]:
        """
        Validate and parse currency input.
        
        Args:
            input_text: User input text
            
        Returns:
            Tuple of (is_valid, parsed_value, error_message)
        """
        if not input_text or not isinstance(input_text, str):
            return False, None, "ورودی خالی است"
        
        parsed_value = cls.parse_persian_number(input_text)
        
        if parsed_value is None:
            return False, None, "فرمت عدد نامعتبر است"
        
        if parsed_value < 0:
            return False, None, "مبلغ نمی‌تواند منفی باشد"
        
        # Check for reasonable limits (adjust as needed)
        max_amount = Decimal('999999999999')  # 999 billion Toman
        if parsed_value > max_amount:
            return False, None, "مبلغ بیش از حد مجاز است"
        
        return True, parsed_value, ""
    
    @classmethod
    def validate_weight_input(cls, input_text: str, unit: str = 'gram') -> Tuple[bool, Optional[Decimal], str]:
        """
        Validate and parse weight input.
        
        Args:
            input_text: User input text
            unit: Weight unit
            
        Returns:
            Tuple of (is_valid, parsed_value, error_message)
        """
        if not input_text or not isinstance(input_text, str):
            return False, None, "ورودی خالی است"
        
        if unit not in cls.WEIGHT_UNITS:
            return False, None, f"واحد وزن نامعتبر: {unit}"
        
        parsed_value = cls.parse_persian_number(input_text)
        
        if parsed_value is None:
            return False, None, "فرمت وزن نامعتبر است"
        
        if parsed_value <= 0:
            return False, None, "وزن باید مثبت باشد"
        
        # Check for reasonable limits (adjust as needed)
        max_weight = Decimal('100000')  # 100kg in grams
        if unit == 'gram' and parsed_value > max_weight:
            return False, None, "وزن بیش از حد مجاز است"
        
        return True, parsed_value, ""