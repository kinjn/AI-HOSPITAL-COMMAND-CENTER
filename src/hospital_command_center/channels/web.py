"""Web form intake adapter."""

from hospital_command_center.channels.base import ChannelAdapter
from hospital_command_center.domain.intake import IntakeChannel, IntakeSubmission


class WebChannel(ChannelAdapter):
    channel = IntakeChannel.WEB

    def to_intake(self, raw: dict) -> IntakeSubmission:
        return IntakeSubmission(
            channel=self.channel,
            symptoms=raw.get("symptoms", ""),
            patient_id=raw.get("patient_id"),
            patient_name=raw.get("patient_name") or raw.get("name"),
            age=raw.get("age"),
            gender=raw.get("gender"),
            phone=raw.get("phone") or raw.get("mobile"),
        )
