"""OpenTelemetry tracing setup (optional)."""
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_tracer_initialized = False

def configure_tracing(service_name: str = 'ai-irule-migrator'):
    global _tracer_initialized
    if _tracer_initialized:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _tracer_initialized = True

def get_tracer(name: str = 'default'):
    return trace.get_tracer(name)
