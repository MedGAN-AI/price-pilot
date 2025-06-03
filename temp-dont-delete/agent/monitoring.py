# monitoring for our agent
import os
import base64
from dotenv import load_dotenv
from opentelemetry.sdk.trace import TracerProvider
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry import trace


# Load environment variables from .env file
load_dotenv()

LANGFUSE_AUTH = base64.b64encode(
    f"{os.environ.get('LANGFUSE_PUBLIC_KEY')}:{os.environ.get('LANGFUSE_SECRET_KEY')}".encode()
).decode()

os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = os.environ.get("LANGFUSE_HOST") + "/api/public/otel"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

# Create a TracerProvider for OpenTelemetry
trace_provider = TracerProvider()

# Add a SimpleSpanProcessor with the OTLPSpanExporter to send traces
trace_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))

# Set the global default tracer provider
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# Instrument Langchain components
LangChainInstrumentor().instrument(tracer_provider=trace_provider)

