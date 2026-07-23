"""WhatsApp intake adapter (stub webhook — Twilio-shaped JSON)."""

from hospital_command_center.channels.base import ChannelAdapter
from hospital_command_center.domain.intake import IntakeChannel, IntakeSubmission


class WhatsAppChannel(ChannelAdapter):
    channel = IntakeChannel.WHATSAPP

    def to_intake(self, raw: dict) -> IntakeSubmission:
        # Stub payload: { "Body": "...", "From": "+91...", "patient_name": "..." }
        # Twilio also sends "Body" and "From" field names.
        return IntakeSubmission(
            channel=self.channel,
            symptoms=raw.get("Body", raw.get("symptoms", "")),
            patient_id=raw.get("patient_id"),
            patient_name=raw.get("patient_name") or raw.get("ProfileName"),
            phone=raw.get("From", raw.get("phone")),
        )
