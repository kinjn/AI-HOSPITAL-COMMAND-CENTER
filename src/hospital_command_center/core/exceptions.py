"""Domain-specific exception hierarchy."""


class HospitalCommandCenterError(Exception):
    """Base error for the application."""


class NotConfiguredError(HospitalCommandCenterError):
    """Raised when required configuration (e.g. API key) is missing."""


class WorkflowError(HospitalCommandCenterError):
    """Raised when a LangGraph workflow step fails."""


class TriageError(HospitalCommandCenterError):
    """Raised when triage LLM classification fails."""


class SummarizationError(HospitalCommandCenterError):
    """Raised when medical summarization fails."""


class RoutingError(HospitalCommandCenterError):
    """Raised when routing fails."""


class IntakeError(HospitalCommandCenterError):
    """Raised when intake validation or persistence fails."""

