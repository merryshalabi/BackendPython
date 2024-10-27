from decimal import Decimal
from core.models import ForeignCurrency

def convert_to_base_currency(amount, currency_code):
    try:
        currency = ForeignCurrency.objects.get(currency_code=currency_code)
        return Decimal(amount) * currency.exchange_rate
    except ForeignCurrency.DoesNotExist:
        raise ValueError(f"Unsupported currency: '{currency_code}'. Please use a supported currency.")
