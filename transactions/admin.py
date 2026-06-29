"""Django admin for transactions — debug + cleanup convenience."""

from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "type",
        "amount",
        "currency",
        "category",
        "counterparty",
        "date",
        "is_deleted",
        "settled_at",
    )
    list_filter = ("type", "currency", "is_deleted")
    search_fields = (
        "user__first_name",
        "user__username",
        "user__telegram_id",
        "counterparty",
        "note",
    )
    date_hierarchy = "date"
    ordering = ("-date", "-id")
    raw_id_fields = ("user", "category")
    readonly_fields = ("created_at", "updated_at", "deleted_at", "settled_at")
