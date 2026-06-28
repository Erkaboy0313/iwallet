from django.contrib import admin

from .models import Quote, QuoteDismissal


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "text_uz", "locale", "is_active")
    list_filter = ("is_active", "locale", "author")
    search_fields = ("author", "text_uz")


@admin.register(QuoteDismissal)
class QuoteDismissalAdmin(admin.ModelAdmin):
    list_display = ("user", "dismissed_at")
