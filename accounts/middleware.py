"""TelegramAuthMiddleware — validates initData on every /app/* request.

Per project-context NFR6: no session cache, revalidate every request.
"""

import logging

from django.conf import settings
from django.http import JsonResponse

from .exceptions import InvalidInitDataError
from .services import get_or_create_user_from_init_data, validate_init_data

logger = logging.getLogger(__name__)

INIT_DATA_HEADER = "HTTP_X_TELEGRAM_INITDATA"
PROTECTED_PATH_PREFIX = "/app/"

# Public shell paths under /app/* that browsers hit on initial page load.
# Telegram WebApp can't attach the initData header to the first GET — the JS SDK
# reads it from the URL fragment AFTER the page loads. These paths render shells
# that fetch real, authenticated content via htmx with the header injected.
PUBLIC_APP_PATHS: frozenset[str] = frozenset(
    {
        "/app/home/",
        "/app/onboarding/",
    }
)


class TelegramAuthMiddleware:
    """Attach `request.user` from validated initData on protected routes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(PROTECTED_PATH_PREFIX):
            return self.get_response(request)

        if request.path in PUBLIC_APP_PATHS:
            return self.get_response(request)

        init_data = request.META.get(INIT_DATA_HEADER, "")
        try:
            user_dict = validate_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)
            request.user = get_or_create_user_from_init_data(user_dict)
        except InvalidInitDataError as e:
            logger.warning("initData validation failed: %s", e)
            return JsonResponse({"error": "invalid_init_data"}, status=401)

        return self.get_response(request)
