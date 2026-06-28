"""Quote of the day — Sprint v0.5 Phase 3.

Curated catalogue of polite, motivational Uzbek finance/discipline quotes.
Selection per-user-per-day is deterministic so the same user sees the same
quote across page refreshes within today.
"""

from django.db import models

from accounts.models import User


class Quote(models.Model):
    text_uz = models.TextField()
    author = models.CharField(max_length=120)
    source = models.CharField(max_length=120, blank=True)
    locale = models.CharField(max_length=8, default="uz")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.author}: {self.text_uz[:48]}…"


class QuoteDismissal(models.Model):
    """One row per user who has opted out of the daily quote."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="quote_dismissal",
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user_id} dismissed at {self.dismissed_at:%Y-%m-%d}"
