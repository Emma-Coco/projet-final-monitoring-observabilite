"""OpenTelemetry configuration for Product Service.

Sets up a TracerProvider that exports spans, via OTLP/HTTP, to the
OpenTelemetry Collector (which in turn forwards them to Jaeger), then
auto-instruments Flask so every incoming HTTP request (e.g. the call coming
from Order Service) becomes a server span in the distributed trace.
"""
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(app, service_name: str):
    """Configures tracing for the given Flask app.

    Args:
        app: the Flask application instance to instrument.
        service_name: value used for the OpenTelemetry "service.name"
            resource attribute, shown in Jaeger as the service.
    """
    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318"
    )

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    # The collector exposes OTLP/HTTP on /v1/traces.
    exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Automatic instrumentation: every Flask route becomes a server span.
    # The W3C trace-context header sent by Order Service's `requests` call
    # is picked up automatically, linking this span to the parent trace.
    FlaskInstrumentor().instrument_app(app)

    return trace.get_tracer(service_name)
