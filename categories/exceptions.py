"""Domain exceptions for the categories app (Epic 3)."""


class CategoryError(Exception):
    """Base class for category-domain errors."""


class InvalidCategoryNameError(CategoryError):
    """Name is empty or too long."""


class DuplicateCategoryError(CategoryError):
    """A category with this name already exists for the user + type."""


class CannotEditPresetError(CategoryError):
    """Tried to edit/delete a preset (user=NULL) category."""


class CannotHideCustomError(CategoryError):
    """Tried to use the preset-hide flow on a custom category."""
