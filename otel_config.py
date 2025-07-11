from junjo.telemetry.junjo_server_otel_exporter import JunjoServerOtelExporter
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from common.settings import settings


def setup_telemetry() -> None:
    """Sets up the OpenTelemetry tracer and exporter for Junjo Server."""
    resource = Resource.create({"service.name": "AI Plays Pokemon Legacy Yellow"})

    tracer_provider = TracerProvider(resource=resource)

    junjo_server_exporter = JunjoServerOtelExporter(
        host="localhost",
        port="50051",
        api_key=settings.junjo_server_api_key,
        insecure=True,
    )

    # Add more span processors here if desired.
    tracer_provider.add_span_processor(junjo_server_exporter.span_processor)
    trace.set_tracer_provider(tracer_provider)
