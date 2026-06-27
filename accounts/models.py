"""Telegram-backed User model. PK is the Telegram user ID (BigInt)."""

from django.db import models

CURRENCY_CHOICES = [
    ("UZS", "so'm"),
    ("RUB", "rubl"),
    ("USD", "dollar"),
]


class User(models.Model):
    """A Telegram user. No passwords — auth is via WebApp initData HMAC."""

    telegram_id = models.BigIntegerField(primary_key=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64, blank=True, default="")
    username = models.CharField(max_length=32, blank=True, default="")
    language_code = models.CharField(max_length=8, default="uz")
    default_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="UZS")
    onboarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    # Marker attributes so middleware-attached user looks "authenticated" to Django views/templates.
    is_authenticated = True
    is_anonymous = False

    class Meta:
        db_table = "accounts_user"

    def __str__(self) -> str:
        return f"@{self.username}" if self.username else f"tg:{self.telegram_id}"
