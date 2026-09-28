"""Azure Application Insights / OpenTelemetry setup for Sports-IQ.

Wires MAF's built-in OTEL instrumentation to Azure Monitor so that every
agent run, tool call, and LLM request appears as a trace in App Insights.

Call setup() exactly once at server startup (before the first request).

Env var required:
    APPLICATIONINSIGHTS_CONNECTION_STRING — copied from App Insights → Overview
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

_TRACER_NAME = "sports-iq"
_configured = False


def setup() -> None:
    """Configure Azure Monitor exporters and enable MAF instrumentation.

    Safe to call multiple times — only runs once.
    """
    global _configured
    if _configured:
        return

    conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    if not conn_str:
        log.warning(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not set — "
            "agent telemetry will not be exported to App Insights. "
            "Set the variable in .env and restart to enable tracing."
        )
        # Still enable MAF instrumentation so traces go to the console exporter
        # if ENABLE_CONSOLE_EXPORTERS=true is set.
        from agent_framework.observability import configure_otel_providers
        configure_otel_providers(enable_console_exporters=False)
        _configured = True
        return

    try:
        from azure.monitor.opentelemetry.exporter import (
            AzureMonitorTraceExporter,
            AzureMonitorLogExporter,
            AzureMonitorMetricExporter,
        )
        from agent_framework.observability import configure_otel_providers, create_metric_views

        exporters = [
            AzureMonitorTraceExporter(connection_string=conn_str),
            AzureMonitorLogExporter(connection_string=conn_str),
            AzureMonitorMetricExporter(connection_string=conn_str),
        ]

        configure_otel_providers(
            exporters=exporters,
            views=create_metric_views(),
            enable_sensitive_data=False,  # flip to True to capture prompts/completions
        )
        log.info("App Insights telemetry configured — traces will appear in Azure Monitor.")
    except Exception as exc:
        log.error("Failed to configure App Insights telemetry: %s", exc)

    _configured = True


def get_tracer():
    """Return the shared OpenTelemetry tracer for manual spans."""
    from opentelemetry import trace
    return trace.get_tracer(_TRACER_NAME)
