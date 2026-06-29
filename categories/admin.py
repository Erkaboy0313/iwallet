"""Django admin for categories — debug + preset management."""

from django.contrib import admin

from .models import Category, CategoryHide


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "emoji", "name", "slug", "is_hidden")
    list_filter = ("type", "is_hidden")
    search_fields = ("name", "slug", "user__first_name", "user__username")
    raw_id_fields = ("user",)
    ordering = ("type", "name")


@admin.register(CategoryHide)
class CategoryHideAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "created_at")
    raw_id_fields = ("user", "category")
