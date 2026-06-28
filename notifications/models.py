"""Notification queue stub — Epic 7 lands the schema, Epic 9 wires the sender.

Per Epic 7 Story 7.3 AC, the recurring tick needs *somewhere* to drop a row so
the Telegram bot process can pick it up. Epic 9 will own the bot consumer +
delivery semantics; this app for now only stores the minimal payload so the
data shape is fixed.
"""

from __future__ import annotations

from django.db import models

from accounts.models import User


class NotificationKind(models.TextChoices):
    RECURRING_FIRED = "recurring_fired", "Takrorlanuvchi yozildi"
    DEBT_DUE = "debt_due", "Qarz muddati keldi"
    DAILY_DIGEST = "daily_digest", "Kunlik xulosa"


class PushQueueItem(models.Model):
    """A pending Telegram push that the bot process will deliver.

    `payload_json` is intentionally a flexible JSONField (not a Pydantic shape)
    because each `kind` carries its own payload (recurring → schedule_id +
    amount; debt → debt_id + party). Epic 9 will introduce per-kind validators
    inside notifications/services.py.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="push_queue_items",
    )
    kind = models.CharField(max_length=32, choices=NotificationKind.choices)
    payload_json = models.JSONField(default=dict, blank=True)

    # Epic 9 will flip this once the bot sends. v1 only writes; consumer TBD.
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_push_queue"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "kind"]),
            models.Index(fields=["sent_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} → {self.user_id} ({self.created_at:%Y-%m-%d})"
