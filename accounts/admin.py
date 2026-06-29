"""Django admin for Telegram users — debug + cleanup convenience."""

from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "first_name",
        "username",
        "default_currency",
        "onboarded_at",
        "created_at",
        "last_seen",
    )
    list_filter = ("default_currency", "language_code")
    search_fields = ("first_name", "last_name", "username", "telegram_id")
    ordering = ("-last_seen",)
    readonly_fields = ("created_at", "last_seen")
