"""Admin for ExchangeRate — read-only-ish row inspection."""

from django.contrib import admin

from currencies.models import ExchangeRate


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "rate_to_uzs", "date", "source", "fetched_at")
    list_filter = ("currency", "source")
    search_fields = ("currency",)
    date_hierarchy = "date"
    ordering = ("-date", "currency")
