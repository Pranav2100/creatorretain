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


class PlanLimitError(DomainError):
    """
    The workspace's plan does not allow this.

    Separate from PermissionDeniedError because the remedy differs:
    a permission failure means ask someone else, a plan failure
    means upgrade. They deserve different HTTP codes and different
    copy in the interface.
    """
