from django.contrib import admin
from core.models import ForeignCurrency , Bank

@admin.register(ForeignCurrency)
class ForeignCurrencyAdmin(admin.ModelAdmin):
    list_display = ('currency_code', 'exchange_rate', 'updated_at')
    search_fields = ('currency_code',)
    list_filter = ('updated_at',)
@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ('balance', 'transaction_fee_percentage','interest_rate')
    readonly_fields = ('balance',)  # Make the balance field read-only

    def has_add_permission(self, request):
        """Prevent adding new bank instances through the admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting the bank instance through the admin"""
        return False