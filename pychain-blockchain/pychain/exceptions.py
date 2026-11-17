"""Custom exceptions so callers can handle failures precisely."""


class PyChainError(Exception):
    """Base class for all PyChain errors."""


class InvalidTransactionError(PyChainError):
    """A transaction is malformed, badly signed or unaffordable."""


class InvalidChainError(PyChainError):
    """The chain failed integrity validation."""


class StorageError(PyChainError):
    """The chain could not be read from or written to disk."""
