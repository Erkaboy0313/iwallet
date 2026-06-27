"""Category model — preset (user=NULL) + user-custom rows (Story 1.3)."""

from django.db import models

from accounts.models import User


class CategoryType(models.TextChoices):
    INCOME = "income", "Kirim"
    EXPENSE = "expense", "Chiqim"


class Category(models.Model):
    """A label for grouping transactions.

    A row with user=NULL is a preset shipped via fixture and visible to every user
    (unless globally hidden). A row with user=<U> is U's custom category.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
        help_text="NULL identifies a preset visible to every user.",
    )
    type = models.CharField(max_length=8, choices=CategoryType.choices)
    slug = models.CharField(max_length=64)
    name = models.CharField(max_length=64)
    emoji = models.CharField(max_length=8, default="📁")
    is_hidden = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categories_category"
        ordering = ["type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "type", "slug"],
                name="categories_unique_slug_per_user_type",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "type"]),
            models.Index(fields=["type", "slug"]),
        ]

    def __str__(self) -> str:
        return f"{self.emoji} {self.name}"

    @property
    def is_preset(self) -> bool:
        return self.user_id is None
