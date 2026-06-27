"""Story 1.3 — seed preset categories on every fresh DB.

Idempotent via update_or_create — safe to re-run; reverses by deleting presets.
"""

from django.db import migrations

PRESETS = [
    # (type, slug, name, emoji)
    ("income", "oylik", "Oylik", "💼"),
    ("income", "biznes", "Biznes", "💼"),
    ("income", "sovga", "Sovg'a", "🎁"),
    ("income", "qaytgan_qarz", "Qaytgan qarz", "🔁"),
    ("income", "boshqa", "Boshqa", "📦"),
    ("expense", "oziq_ovqat", "Oziq-ovqat", "🛒"),
    ("expense", "transport", "Transport", "🚗"),
    ("expense", "taxi", "Taxi", "🚕"),
    ("expense", "qahva_kafe", "Qahva/kafe", "☕"),
    ("expense", "kommunal", "Kommunal", "🧾"),
    ("expense", "kongilochar", "Ko'ngilochar", "🎮"),
    ("expense", "kiyim", "Kiyim", "👕"),
    ("expense", "sogliq", "Sog'liq", "💊"),
    ("expense", "talim", "Ta'lim", "📚"),
    ("expense", "boshqa", "Boshqa", "📦"),
]


def seed_presets(apps, _schema_editor):
    Category = apps.get_model("categories", "Category")
    for type_, slug, name, emoji in PRESETS:
        Category.objects.update_or_create(
            user=None,
            type=type_,
            slug=slug,
            defaults={"name": name, "emoji": emoji, "is_hidden": False},
        )


def remove_presets(apps, _schema_editor):
    Category = apps.get_model("categories", "Category")
    Category.objects.filter(user__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed_presets, remove_presets),
    ]
