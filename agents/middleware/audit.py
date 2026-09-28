"""Audit middleware — logs every tool call and result for demo observability.

Uses MAF FunctionMiddleware, which intercepts individual @tool function calls
before and after execution. Registered on each Agent via middleware=[...].
"""
import json
import logging

from agent_framework import FunctionMiddleware

log = logging.getLogger("sports-iq.audit")


class AuditFunctionMiddleware(FunctionMiddleware):
    """Intercepts every tool call: logs name, arguments, and result."""

    async def process(self, context, call_next):
        fn_name = context.function.name
        args = context.arguments or {}
        log.info("[AUDIT] → %s(%s)", fn_name, json.dumps(dict(args), default=str)[:300])

        await call_next()

        result_preview = str(context.result)[:300] if context.result is not None else "None"
        log.info("[AUDIT] ← %s → %s", fn_name, result_preview)
