"""Channel adapter interface and message normalization."""

from abc import ABC, abstractmethod

from hospital_command_center.domain.intake import IntakeChannel, IntakeSubmission


class ChannelAdapter(ABC):
    channel: IntakeChannel

    @abstractmethod
    def to_intake(self, raw: dict) -> IntakeSubmission:
        """Map channel-specific payload to IntakeSubmission."""
