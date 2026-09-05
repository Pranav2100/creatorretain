class DomainError(ValueError):
    """
    Base class for all business-rule failures.

    Inherits from ValueError so that existing routers using
    `except ValueError` keep working unchanged.
    """


class NotFoundError(DomainError):
    """The requested resource does not exist."""


class PermissionDeniedError(DomainError):
    """The current user is not allowed to perform this action."""


class ConflictError(DomainError):
    """The action conflicts with the current state of the resource."""
