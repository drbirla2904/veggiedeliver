from django.contrib import admin
from .models import Wallet, WalletTransaction, ReferralSettings


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ("type", "amount", "reason", "related_order", "created_at")
    can_delete = False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance")
    search_fields = ("user__mobile",)
    inlines = [WalletTransactionInline]
    readonly_fields = ("balance",)


@admin.register(ReferralSettings)
class ReferralSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "bonus_amount", "min_order_value_for_bonus", "max_wallet_usage_percent",
        "minimum_order_amount", "delivery_charge", "free_delivery_minimum",
    )

    def has_add_permission(self, request):
        return not ReferralSettings.objects.exists()
