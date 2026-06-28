"""Admin registration for the recurring app (Epic 7)."""

from django.contrib import admin

from .models import RecurringSchedule


@admin.register(RecurringSchedule)
class RecurringScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "name",
        "type",
        "amount",
        "currency",
        "schedule_kind",
        "next_dispatch_at",
        "is_active",
    )
    list_filter = ("schedule_kind", "type", "is_active", "currency")
    search_fields = ("name", "user__username", "user__first_name")
    raw_id_fields = ("user", "category")
