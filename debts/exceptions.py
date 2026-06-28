"""Domain exceptions for the debts app (Story 4.1).

Every concrete failure inherits from :class:`DebtError` so callers can `except`
broadly without catching unrelated bugs.
"""


class DebtError(Exception):
    """Base exception — every debt-domain failure inherits from this."""


class DebtAlreadyClosedError(DebtError):
    """Repayment / mutation attempted on a closed or cancelled debt."""


class CurrencyMismatchError(DebtError):
    """Repayment currency doesn't match the debt's currency (v1 limitation)."""


class RepaymentExceedsRemainingError(DebtError):
    """Repayment amount is greater than the remaining balance on the debt."""


class InvalidDebtAmountError(DebtError):
    """Amount must be strictly positive (no zero / no negative)."""
