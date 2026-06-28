"""Domain exceptions for the recurring app (Epic 7)."""


class RecurringError(Exception):
    """Base class for recurring-domain errors."""


class InvalidScheduleError(RecurringError):
    """Schedule kind/day-of-month/day-of-week combination is malformed."""


class InvalidAmountError(RecurringError):
    """Amount is missing, zero, or negative."""


class InvalidNameError(RecurringError):
    """Name is empty or too long."""
