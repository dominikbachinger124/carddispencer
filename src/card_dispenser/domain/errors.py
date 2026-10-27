"""Domain-level errors shared by services and the UI."""


class DomainError(Exception):
    """Base class for errors that are meaningful to the user or a service."""
