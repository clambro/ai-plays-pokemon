"""Logfire configuration for application telemetry."""

import logfire
from loguru import logger

from common.settings import settings


def setup_telemetry() -> None:
    """Configure Logfire and instrument the OpenAI client."""
    if not settings.logfire_token:
        logger.warning("LOGFIRE_TOKEN is not set; telemetry will not be sent to Logfire.")

    logfire.configure(
        send_to_logfire="if-token-present",
        token=settings.logfire_token or None,
        service_name="AI Plays Pokemon Yellow Legacy",
        console=False,
    )
    logfire.instrument_openai()
