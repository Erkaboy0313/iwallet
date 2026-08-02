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
    # Sprint v0.8 — weekly ping on still-open raw debt transactions (7 days
    # old, no follow-up). Separate from DEBT_DUE which is tied to an
    # explicit expected_return_date on the Debt aggregate.
    DEBT_REMINDER = "debt_reminder", "Qarz eslatmasi"


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


class AdminMessageLink(models.Model):
    """Maps a message the bot sent into the admin's chat back to the user
    who originally sent it. When the admin replies to that message, the
    handler looks up the row to find the target user.

    Text-only for MVP. `user_telegram_id` is the raw Telegram id (not a FK to
    accounts.User) because the sender may not be a registered WebApp user yet.

    For future media support: extend the "message" concept by adding
    downstream fields here (e.g. `content_kind`) without touching the
    existing shape — the reply-routing lookup only needs
    `(admin_chat_id, admin_message_id) → user_telegram_id`.
    """

    admin_chat_id = models.BigIntegerField()
    admin_message_id = models.BigIntegerField()
    user_telegram_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["admin_chat_id", "admin_message_id"]),
        ]
        # Same (chat_id, message_id) can't map to two different users.
        constraints = [
            models.UniqueConstraint(
                fields=["admin_chat_id", "admin_message_id"],
                name="notifications_admin_message_link_unique",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"admin_msg({self.admin_chat_id}:{self.admin_message_id})"
            f" → user={self.user_telegram_id}"
        )
