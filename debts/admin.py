"""Django admin registration for Debt + DebtRepayment (debugging convenience)."""

from django.contrib import admin

from .models import Debt, DebtRepayment


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "direction",
        "counterparty",
        "remaining_amount",
        "original_amount",
        "currency",
        "state",
        "created_at",
    )
    list_filter = ("state", "direction", "currency")
    search_fields = ("counterparty", "user__first_name", "user__username")


@admin.register(DebtRepayment)
class DebtRepaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "debt", "amount", "repaid_at", "created_at")
    list_filter = ("repaid_at",)
