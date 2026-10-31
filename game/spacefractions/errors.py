"""Authorization errors and helpers for the User/Admin service boundaries."""


class AuthorizationError(Exception):
    """Raised when an actor lacks permission to perform an action."""


class AuthenticationError(Exception):
    """Raised when credentials cannot be verified."""


class StorageError(Exception):
    """Raised when the persistence layer cannot complete an operation."""
