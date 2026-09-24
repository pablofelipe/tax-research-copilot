from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

DEFAULT_OTLP_ENDPOINT = "http://localhost:4318/v1/traces"


def configure_tracing(service_name: str, otlp_endpoint: str = DEFAULT_OTLP_ENDPOINT) -> None:
    """Configures the global TracerProvider to export spans over OTLP.

    Call once, from a composition root only (app.main, app.evaluate) —
    never from a module that unit tests import, since tests never call
    this and rely on OpenTelemetry's default no-op tracer instead.
    """
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
