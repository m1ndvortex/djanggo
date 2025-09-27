"""
Persian contract templates for gold installment system.
Provides legal terms and payment schedules in Persian.
"""
from typing import Dict, Any
from decimal import Decimal
from datetime import date, timedelta
from zargar.core.persian_number_formatter import PersianNumberFormatter
from zargar.core.calendar_utils import PersianCalendarUtils


class GoldInstallmentContractTemplates:
    """
    Persian contract templates for gold installment agreements.
    """
    
    @staticmethod
    def get_standard_contract_terms() -> str:
        """
        Get standard Persian contract terms for gold installment agreements.
        
        Returns:
            Standard contract terms in Persian
        """
        return """
قرارداد طلای قرضی

شرایط عمومی:

۱. تعاریف:
   - طلای قرضی: طلایی که توسط مشتری از طلافروشی دریافت شده و باید طبق شرایط این قرارداد بازپرداخت شود.
   - وزن طلا: وزن خالص طلا بر حسب گرم که مبنای محاسبات قرار می‌گیرد.
   - قیمت روز: قیمت طلا در بازار تهران که روزانه تعیین می‌شود.

۲. تعهدات مشتری:
   - بازپرداخت کامل وزن طلای دریافتی طبق برنامه پرداخت تعیین شده
   - پرداخت منظم اقساط در تاریخ‌های مقرر
   - اطلاع‌رسانی فوری در صورت تغییر آدرس یا شماره تماس
   - رعایت شرایط و ضوابط این قرارداد

۳. تعهدات طلافروشی:
   - ارائه طلای با کیفیت و عیار مشخص شده
   - محاسبه دقیق وزن و ارزش طلا
   - ارائه رسید و مدارک مربوطه
   - اطلاع‌رسانی تغییرات قیمت طلا

۴. شرایط پرداخت:
   - پرداخت‌ها بر اساس وزن طلا و قیمت روز محاسبه می‌شود
   - هر پرداخت معادل وزن طلای مربوطه از بدهی کسر می‌شود
   - امکان پرداخت زودتر با تخفیف مقرر وجود دارد
   - تأخیر در پرداخت مشمول جریمه خواهد بود

۵. ضمانت‌ها:
   - مشتری متعهد است ضمانت‌های لازم را ارائه دهد
   - در صورت عدم پرداخت، طلافروشی حق مراجعه به ضمانت‌ها را دارد
   - ضمانت‌ها پس از تسویه کامل بدهی آزاد خواهد شد

۶. شرایط خاص:
   - این قرارداد تابع قوانین جمهوری اسلامی ایران است
   - هرگونه اختلاف از طریق مراجع قضایی حل و فصل خواهد شد
   - تغییر شرایط قرارداد نیازمند توافق کتبی طرفین است

۷. فسخ قرارداد:
   - قرارداد با تسویه کامل بدهی خاتمه می‌یابد
   - طلافروشی در صورت تخلف مشتری حق فسخ قرارداد را دارد
   - فسخ قرارداد مستلزم تسویه فوری کل بدهی است

امضای طرفین این قرارداد به منزله پذیرش کلیه شرایط فوق می‌باشد.
        """.strip()
    
    @staticmethod
    def get_payment_schedule_terms(schedule_type: str) -> str:
        """
        Get payment schedule terms in Persian.
        
        Args:
            schedule_type: Type of payment schedule (weekly, bi_weekly, monthly, custom)
            
        Returns:
            Payment schedule terms in Persian
        """
        terms = {
            'weekly': """
برنامه پرداخت هفتگی:
- پرداخت‌ها هر هفته یکبار انجام می‌شود
- روز پرداخت: همان روز هفته که قرارداد منعقد شده
- حداکثر تأخیر مجاز: ۳ روز کاری
- در صورت تأخیر بیش از ۳ روز، جریمه تأخیر اعمال می‌شود
            """,
            
            'bi_weekly': """
برنامه پرداخت دو هفته‌ای:
- پرداخت‌ها هر دو هفته یکبار انجام می‌شود
- روز پرداخت: همان روز هفته که قرارداد منعقد شده
- حداکثر تأخیر مجاز: ۵ روز کاری
- در صورت تأخیر بیش از ۵ روز، جریمه تأخیر اعمال می‌شود
            """,
            
            'monthly': """
برنامه پرداخت ماهانه:
- پرداخت‌ها هر ماه یکبار انجام می‌شود
- روز پرداخت: همان روز ماه که قرارداد منعقد شده
- حداکثر تأخیر مجاز: ۷ روز کاری
- در صورت تأخیر بیش از ۷ روز، جریمه تأخیر اعمال می‌شود
            """,
            
            'custom': """
برنامه پرداخت سفارشی:
- پرداخت‌ها طبق توافق خاص طرفین انجام می‌شود
- تاریخ‌های پرداخت در ضمیمه قرارداد مشخص شده است
- حداکثر تأخیر مجاز: طبق توافق
- شرایط جریمه تأخیر در ضمیمه قرارداد آمده است
            """
        }
        
        return terms.get(schedule_type, terms['monthly']).strip()
    
    @staticmethod
    def get_price_protection_terms(has_protection: bool, ceiling: Decimal = None, floor: Decimal = None) -> str:
        """
        Get price protection terms in Persian.
        
        Args:
            has_protection: Whether price protection is enabled
            ceiling: Price ceiling per gram
            floor: Price floor per gram
            
        Returns:
            Price protection terms in Persian
        """
        if not has_protection:
            return """
حفاظت قیمت:
- این قرارداد فاقد حفاظت قیمت است
- محاسبات بر اساس قیمت روز طلا انجام می‌شود
- تغییرات قیمت طلا بر روی مبلغ پرداخت‌ها تأثیر خواهد گذاشت
            """.strip()
        
        formatter = PersianNumberFormatter()
        terms = "حفاظت قیمت:\n- این قرارداد دارای حفاظت قیمت است\n"
        
        if ceiling:
            ceiling_display = formatter.format_currency(ceiling, use_persian_digits=True)
            terms += f"- حداکثر قیمت محاسباتی: {ceiling_display} در هر گرم\n"
        
        if floor:
            floor_display = formatter.format_currency(floor, use_persian_digits=True)
            terms += f"- حداقل قیمت محاسباتی: {floor_display} در هر گرم\n"
        
        terms += "- قیمت‌های خارج از محدوده تعیین شده تأثیری بر محاسبات نخواهد داشت"
        
        return terms.strip()
    
    @staticmethod
    def get_early_payment_terms(discount_percentage: Decimal) -> str:
        """
        Get early payment discount terms in Persian.
        
        Args:
            discount_percentage: Early payment discount percentage
            
        Returns:
            Early payment terms in Persian
        """
        if discount_percentage <= 0:
            return """
پرداخت زودهنگام:
- این قرارداد فاقد تخفیف پرداخت زودهنگام است
- تسویه زودتر از موعد مقرر بدون تخفیف انجام می‌شود
            """.strip()
        
        formatter = PersianNumberFormatter()
        discount_display = formatter.format_percentage(discount_percentage, use_persian_digits=True)
        
        return f"""
پرداخت زودهنگام:
- در صورت تسویه کامل قبل از موعد مقرر، تخفیف {discount_display} اعمال می‌شود
- تخفیف بر اساس ارزش باقیمانده طلا در زمان تسویه محاسبه می‌شود
- برای استفاده از تخفیف، مشتری باید کل بدهی را یکجا پرداخت کند
- تخفیف قابل تجمیع با سایر تخفیف‌ها نیست
        """.strip()
    
    @staticmethod
    def generate_complete_contract(contract_data: Dict[str, Any]) -> str:
        """
        Generate complete contract document in Persian.
        
        Args:
            contract_data: Dictionary containing contract information
            
        Returns:
            Complete contract document in Persian
        """
        formatter = PersianNumberFormatter()
        calendar_utils = PersianCalendarUtils()
        
        # Extract contract data
        contract_number = contract_data.get('contract_number', 'نامشخص')
        customer_name = contract_data.get('customer_name', 'نامشخص')
        contract_date = contract_data.get('contract_date', date.today())
        initial_weight = contract_data.get('initial_weight_grams', Decimal('0'))
        gold_karat = contract_data.get('gold_karat', 18)
        payment_schedule = contract_data.get('payment_schedule', 'monthly')
        has_price_protection = contract_data.get('has_price_protection', False)
        price_ceiling = contract_data.get('price_ceiling_per_gram')
        price_floor = contract_data.get('price_floor_per_gram')
        early_payment_discount = contract_data.get('early_payment_discount_percentage', Decimal('0'))
        
        # Format values
        shamsi_date = calendar_utils.gregorian_to_shamsi(contract_date)
        contract_date_display = calendar_utils.format_persian_date(shamsi_date)
        weight_display = formatter.format_weight(initial_weight, 'gram', use_persian_digits=True)
        karat_display = formatter.to_persian_digits(str(gold_karat))
        
        # Build complete contract
        contract = f"""
بسم الله الرحمن الرحیم

قرارداد طلای قرضی

شماره قرارداد: {contract_number}
تاریخ انعقاد: {contract_date_display}

طرفین قرارداد:
الف) طلافروشی: [نام طلافروشی]
ب) مشتری: {customer_name}

مشخصات طلای قرضی:
- وزن کل: {weight_display}
- عیار طلا: {karat_display} عیار
- نوع طلا: [مشخصات طلا]

{GoldInstallmentContractTemplates.get_standard_contract_terms()}

برنامه پرداخت:
{GoldInstallmentContractTemplates.get_payment_schedule_terms(payment_schedule)}

{GoldInstallmentContractTemplates.get_price_protection_terms(has_price_protection, price_ceiling, price_floor)}

{GoldInstallmentContractTemplates.get_early_payment_terms(early_payment_discount)}

شرایط خاص این قرارداد:
- [شرایط اضافی در صورت وجود]

تاریخ انعقاد: {contract_date_display}
محل انعقاد: [آدرس طلافروشی]

امضای طرفین:

طلافروشی: ________________    مشتری: ________________

[مهر طلافروشی]              تاریخ: {contract_date_display}
        """.strip()
        
        return contract
    
    @staticmethod
    def get_payment_receipt_template() -> str:
        """
        Get payment receipt template in Persian.
        
        Returns:
            Payment receipt template in Persian
        """
        return """
رسید پرداخت طلای قرضی

شماره قرارداد: {contract_number}
نام مشتری: {customer_name}
تاریخ پرداخت: {payment_date_shamsi}

جزئیات پرداخت:
- مبلغ پرداختی: {payment_amount_display}
- قیمت طلا در زمان پرداخت: {gold_price_display}
- معادل وزن طلا: {gold_weight_display}
- روش پرداخت: {payment_method_display}

وضعیت قرارداد:
- وزن باقیمانده: {remaining_weight_display}
- درصد تکمیل: {completion_percentage_display}
- کل پرداخت‌ها: {total_payments_display}

{discount_info}

تاریخ صدور رسید: {receipt_date}
شماره رسید: {receipt_number}

[مهر و امضای طلافروشی]
        """.strip()
    
    @staticmethod
    def get_adjustment_authorization_template() -> str:
        """
        Get weight adjustment authorization template in Persian.
        
        Returns:
            Adjustment authorization template in Persian
        """
        return """
مجوز تعدیل وزن طلای قرضی

شماره قرارداد: {contract_number}
نام مشتری: {customer_name}
تاریخ تعدیل: {adjustment_date_shamsi}

جزئیات تعدیل:
- وزن قبل از تعدیل: {weight_before_display}
- مقدار تعدیل: {adjustment_amount_display}
- وزن پس از تعدیل: {weight_after_display}
- نوع تعدیل: {adjustment_type_display}
- دلیل تعدیل: {adjustment_reason_display}

توضیحات:
{description}

مجوز دهنده: {authorized_by}
تاریخ مجوز: {authorization_date}

{authorization_notes}

[مهر و امضای مسئول]
        """.strip()
    
    @staticmethod
    def get_contract_completion_certificate() -> str:
        """
        Get contract completion certificate template in Persian.
        
        Returns:
            Contract completion certificate in Persian
        """
        return """
گواهی تکمیل قرارداد طلای قرضی

شماره قرارداد: {contract_number}
نام مشتری: {customer_name}
تاریخ شروع قرارداد: {contract_start_date}
تاریخ تکمیل قرارداد: {completion_date}

مشخصات قرارداد:
- وزن اولیه طلا: {initial_weight_display}
- کل مبلغ پرداختی: {total_payments_display}
- تعداد پرداخت‌ها: {total_payment_count}
- مدت قرارداد: {contract_duration} روز

بدین وسیله گواهی می‌شود که آقای/خانم {customer_name} تعهدات خود را طبق قرارداد شماره {contract_number} به طور کامل ایفا نموده و هیچگونه بدهی‌ای نسبت به این طلافروشی ندارد.

کلیه ضمانت‌ها و تعهدات مربوط به این قرارداد لغو و ملغی اعلام می‌شود.

تاریخ صدور: {certificate_date}
شماره گواهی: {certificate_number}

[مهر و امضای طلافروشی]
        """.strip()
    
    @staticmethod
    def get_default_reminder_template() -> str:
        """
        Get payment reminder template in Persian.
        
        Returns:
            Payment reminder template in Persian
        """
        return """
یادآوری پرداخت طلای قرضی

آقای/خانم محترم {customer_name}

با سلام و احترام،

بدین وسیله یادآور می‌شویم که طبق قرارداد شماره {contract_number} مورخ {contract_date}، موعد پرداخت بعدی شما {next_payment_date} می‌باشد.

جزئیات قرارداد:
- وزن باقیمانده: {remaining_weight_display}
- ارزش تقریبی (بر اساس قیمت روز): {estimated_value_display}
- درصد تکمیل: {completion_percentage_display}

لطفاً جهت پرداخت و یا هماهنگی با این طلافروشی تماس حاصل فرمایید.

آدرس: [آدرس طلافروشی]
تلفن: [شماره تماس]

با تشکر
[نام طلافروشی]
        """.strip()


class ContractDocumentGenerator:
    """
    Helper class for generating contract documents with proper formatting.
    """
    
    @staticmethod
    def format_contract_data(contract) -> Dict[str, Any]:
        """
        Format contract data for document generation.
        
        Args:
            contract: GoldInstallmentContract instance
            
        Returns:
            Formatted contract data dictionary
        """
        formatter = PersianNumberFormatter()
        
        return {
            'contract_number': contract.contract_number,
            'customer_name': str(contract.customer),
            'contract_date': contract.contract_date,
            'initial_weight_grams': contract.initial_gold_weight_grams,
            'gold_karat': contract.gold_karat,
            'payment_schedule': contract.payment_schedule,
            'has_price_protection': contract.has_price_protection,
            'price_ceiling_per_gram': contract.price_ceiling_per_gram,
            'price_floor_per_gram': contract.price_floor_per_gram,
            'early_payment_discount_percentage': contract.early_payment_discount_percentage,
        }
    
    @staticmethod
    def format_payment_data(payment) -> Dict[str, str]:
        """
        Format payment data for receipt generation.
        
        Args:
            payment: GoldInstallmentPayment instance
            
        Returns:
            Formatted payment data dictionary
        """
        formatter = PersianNumberFormatter()
        
        # Calculate remaining weight and completion
        contract = payment.contract
        remaining_weight_display = formatter.format_weight(
            contract.remaining_gold_weight_grams, 'gram', use_persian_digits=True
        )
        completion_percentage_display = formatter.format_percentage(
            contract.completion_percentage, use_persian_digits=True
        )
        
        # Format discount info if applicable
        discount_info = ""
        if payment.discount_applied:
            discount_display = formatter.format_currency(
                payment.discount_amount_toman, use_persian_digits=True
            )
            discount_percentage_display = formatter.format_percentage(
                payment.discount_percentage, use_persian_digits=True
            )
            discount_info = f"تخفیف اعمال شده: {discount_percentage_display} ({discount_display})"
        
        return {
            'contract_number': contract.contract_number,
            'customer_name': str(contract.customer),
            'payment_date_shamsi': payment.payment_date_shamsi,
            'payment_amount_display': formatter.format_currency(
                payment.payment_amount_toman, use_persian_digits=True
            ),
            'gold_price_display': formatter.format_currency(
                payment.gold_price_per_gram_at_payment, use_persian_digits=True
            ),
            'gold_weight_display': formatter.format_weight(
                payment.gold_weight_equivalent_grams, 'gram', use_persian_digits=True
            ),
            'payment_method_display': payment.get_payment_method_display(),
            'remaining_weight_display': remaining_weight_display,
            'completion_percentage_display': completion_percentage_display,
            'total_payments_display': formatter.format_currency(
                contract.total_payments_received, use_persian_digits=True
            ),
            'discount_info': discount_info,
            'receipt_date': PersianCalendarUtils.format_persian_date(
                PersianCalendarUtils.get_current_persian_date()
            ),
            'receipt_number': f"R-{payment.id:06d}"
        }
    
    @staticmethod
    def format_adjustment_data(adjustment) -> Dict[str, str]:
        """
        Format adjustment data for authorization document.
        
        Args:
            adjustment: GoldWeightAdjustment instance
            
        Returns:
            Formatted adjustment data dictionary
        """
        formatter = PersianNumberFormatter()
        
        return {
            'contract_number': adjustment.contract.contract_number,
            'customer_name': str(adjustment.contract.customer),
            'adjustment_date_shamsi': adjustment.adjustment_date_shamsi,
            'weight_before_display': formatter.format_weight(
                adjustment.weight_before_grams, 'gram', use_persian_digits=True
            ),
            'adjustment_amount_display': formatter.format_weight(
                abs(adjustment.adjustment_amount_grams), 'gram', use_persian_digits=True
            ),
            'weight_after_display': formatter.format_weight(
                adjustment.weight_after_grams, 'gram', use_persian_digits=True
            ),
            'adjustment_type_display': adjustment.get_adjustment_type_display(),
            'adjustment_reason_display': adjustment.get_adjustment_reason_display(),
            'description': adjustment.description,
            'authorized_by': str(adjustment.authorized_by),
            'authorization_date': PersianCalendarUtils.format_persian_date(
                PersianCalendarUtils.gregorian_to_shamsi(adjustment.adjustment_date)
            ),
            'authorization_notes': adjustment.authorization_notes or 'ندارد'
        }