"""Auth-related exceptions for the accounts app."""


class TelegramAuthError(Exception):
    """Base class for Telegram initData validation failures."""


class InvalidInitDataError(TelegramAuthError):
    """initData is malformed, has bad HMAC, or is expired."""


class MissingInitDataError(TelegramAuthError):
    """No initData header on a /app/* request."""
