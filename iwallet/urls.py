"""Root URL conf. /app/* is auth-protected by TelegramAuthMiddleware."""

from django.contrib import admin
from django.urls import include, path

from core.views import healthz

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    path("app/", include("core.urls")),
    path("app/", include("accounts.urls")),
    path("app/", include("transactions.urls")),
    path("app/", include("debts.urls")),
    path("app/", include("currencies.urls")),
]
