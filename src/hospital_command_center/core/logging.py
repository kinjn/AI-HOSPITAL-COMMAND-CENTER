"""Structured logging setup."""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from hospital_command_center.core.config import get_settings

LOG_DIR = Path("data/logs")
LOG_FILE = LOG_DIR / "app.log"

# Standard LogRecord attributes — anything else on the record is "extra" context
# that callers passed in, e.g. logger.info("msg", extra={"encounter_id": "..."})
_STANDARD_ATTRS = set(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys())


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON, including any extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Pull in any extra kwargs the caller attached (encounter_id, error, etc.)
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console format that still surfaces `extra` context.

    The previous formatter only rendered `%(message)s`, which silently
    dropped anything passed via `logger.warning(msg, extra={"error": ...})`.
    On Render (and most PaaS setups) the console/stdout stream is the *only*
    thing visible in the dashboard's log viewer — the JSON file handler below
    writes to local disk, which isn't reachable there and may not even
    survive a redeploy. So any detail that only goes to the file handler is
    effectively invisible in production. This formatter appends the extra
    fields (and any exception traceback) to the console line as well.
    """

    def format(self, record: logging.LogRecord) -> str:
        base = f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} {record.levelname} [{record.name}] {record.getMessage()}"

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_ATTRS
        }
        if extras:
            base += " | " + json.dumps(extras, default=str)

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


def configure_logging() -> None:
    settings = get_settings()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers if configure_logging() is called more than once
    # (e.g. once on import, once again under uvicorn --reload)
    root_logger.handlers.clear()

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ConsoleFormatter())
    root_logger.addHandler(console_handler)

    # Quiet uvicorn's file-watcher noise — it logs every detected change at INFO
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance."""
    return logging.getLogger(name)