"""TelegramAuthMiddleware — auths /app/* via initData header OR sticky session.

Plain <a href> navigation in Telegram WebView can't inject the initData header
(JS only runs for htmx requests), so once initData has been validated for the
WebApp session we cache the telegram_id in Django's session cookie and let
follow-up navigation requests reuse it. The cookie itself is signed by Django;
without a valid initData revalidation it just expires with the WebApp session.
"""

import logging

from django.conf import settings
from django.http import JsonResponse

from .exceptions import InvalidInitDataError
from .models import User
from .services import get_or_create_user_from_init_data, validate_init_data

logger = logging.getLogger(__name__)

INIT_DATA_HEADER = "HTTP_X_TELEGRAM_INITDATA"
SESSION_KEY = "telegram_user_id"
PROTECTED_PATH_PREFIX = "/app/"

# Public shell paths under /app/* that browsers hit on initial page load.
# Telegram WebApp can't attach the initData header to the first GET — the JS SDK
# reads it from the URL fragment AFTER the page loads. These paths render shells
# that fetch real, authenticated content via htmx with the header injected.
PUBLIC_APP_PATHS: frozenset[str] = frozenset(
    {
        "/app/home/",
        "/app/home/content/",
        "/app/onboarding/",
    }
)


class CsrfExemptAppMiddleware:
    """Bypass Django's CSRF token check for /app/* routes.

    Every protected /app/* endpoint is already authenticated by an HMAC-signed
    Telegram initData header (or a sticky session derived from one). An attacker
    can't forge that without the bot token — strictly stronger than the CSRF
    token would be — so the CSRF middleware would only add ceremony to the
    htmx layer (no <form>, no csrfmiddlewaretoken to splice in) without
    adding real protection. Must be installed BEFORE CsrfViewMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(PROTECTED_PATH_PREFIX):
            request._dont_enforce_csrf_checks = True
        return self.get_response(request)


class TelegramAuthMiddleware:
    """Attach `request.user` from validated initData (or sticky session)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(PROTECTED_PATH_PREFIX):
            return self.get_response(request)

        if request.path in PUBLIC_APP_PATHS:
            return self.get_response(request)

        init_data = request.META.get(INIT_DATA_HEADER, "")
        if init_data:
            try:
                user_dict = validate_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)
                user = get_or_create_user_from_init_data(user_dict)
                _remember(request, user.telegram_id)
                request.user = user
                return self.get_response(request)
            except InvalidInitDataError as e:
                logger.warning("initData validation failed: %s", e)
                return JsonResponse({"error": "invalid_init_data"}, status=401)

        session = getattr(request, "session", None)
        cached_id = session.get(SESSION_KEY) if session is not None else None
        if cached_id is not None:
            try:
                request.user = User.objects.get(telegram_id=cached_id)
                return self.get_response(request)
            except User.DoesNotExist:
                session.pop(SESSION_KEY, None)

        logger.info("no initData header and no session for path=%s", request.path)
        return JsonResponse({"error": "invalid_init_data"}, status=401)


def _remember(request, telegram_id: int) -> None:
    """Stash the validated telegram_id on the request session if available.

    RequestFactory-built requests in tests don't have a session attached;
    skipping there keeps the middleware unit-testable without extra setup.
    """
    session = getattr(request, "session", None)
    if session is not None:
        session[SESSION_KEY] = telegram_id
