# TraceHarbor Python Tracing SDK

The client-side tracing library for AI agents, multi-agent frameworks, and LLM applications.

## Status: Phase 1 Planned

This package will be implemented in **Phase 1: Tracing Engine**.

### Target Features:
- **Zero-Friction Context Managers**: `with client.trace(name="...") as run:`
- **Nested Span Tracking**: Automatic parent-child relationship handling for LLM and tool calls.
- **Asynchronous Batching**: Background thread queue with timed/batched flushing to minimize agent latency overhead (<5ms).
- **Auto-Instrumentation**: Support for OpenAI, Anthropic, and LangChain agents.
