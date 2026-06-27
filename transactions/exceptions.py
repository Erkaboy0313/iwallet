"""Domain exceptions for the transactions app."""


class TransactionError(Exception):
    """Base — every concrete failure inherits from this so callers can `except` broadly."""


class InvalidAmountError(TransactionError):
    """Amount must be positive (project-context rule: never accept zero/negative)."""


class RestoreExpiredError(TransactionError):
    """Soft-delete restore window (7 days per FR8) has elapsed."""


class TransactionNotEditableError(TransactionError):
    """Transaction is soft-deleted; cannot mutate. Restore first."""
