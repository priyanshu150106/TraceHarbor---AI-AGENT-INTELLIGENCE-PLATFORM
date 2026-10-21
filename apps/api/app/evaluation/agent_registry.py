"""
TraceHarbor API — Approved Agent Registry & Safe Execution Adapters

TraceHarbor enforces safe execution through an explicit adapter registry.
Arbitrary user-uploaded code or modules are NEVER imported or executed.
Only registered, approved agent implementations and versions can be evaluated.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

# Knowledge base for deterministic support agents
KNOWLEDGE_BASE = {
    "return": "Customers can return items within 30 days of purchase for a full refund or exchange.",
    "policy": "Customers can return items within 30 days of purchase for a full refund or exchange.",
    "shipping": "Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days.",
    "warranty": "All electronic devices include a standard 1-year limited hardware warranty.",
    "refund": "Refunds are processed to the original payment method within 5-7 business days.",
}


@dataclass
class AgentExecutionResult:
    """Output and execution telemetry captured from an approved agent run."""

    output: Any
    duration_ms: int
    total_tokens: int
    total_cost_usd: Decimal
    spans: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    status: str = "completed"


class BaseAgentAdapter(ABC):
    """Abstract interface for approved agents."""

    name: str
    version: str
    description: str

    @abstractmethod
    async def execute(self, prompt_input: Any, config: dict[str, Any] | None = None) -> AgentExecutionResult:
        """Execute the agent against a test prompt."""
        pass


class SupportAgentV1(BaseAgentAdapter):
    """
    Standard customer support reasoning agent (v1.0).
    Performs knowledge base lookup and simulated LLM synthesis.
    """

    name = "support_agent"
    version = "1.0"
    description = "Standard customer support reasoning agent with FAQ retrieval"

    async def execute(self, prompt_input: Any, config: dict[str, Any] | None = None) -> AgentExecutionResult:
        start_time = time.perf_counter()
        query = str(prompt_input.get("query", prompt_input) if isinstance(prompt_input, dict) else prompt_input)
        query_lower = query.lower()

        # Step 1: Tool span - knowledge_base_search
        t0 = datetime.now(UTC)
        await asyncio.sleep(0.02)  # Simulated I/O latency
        t1 = datetime.now(UTC)

        matched_kb = "No specific FAQ article found. General customer support assistance will be provided."
        for k, v in KNOWLEDGE_BASE.items():
            if k in query_lower:
                matched_kb = v
                break

        kb_span = {
            "name": "knowledge_base_search",
            "span_type": "tool",
            "status": "completed",
            "input": {"query": query},
            "output": {"result": matched_kb},
            "model": "kb-embed-v1",
            "prompt_tokens": 25,
            "completion_tokens": 30,
            "total_tokens": 55,
            "cost_usd": 0.00011,
            "duration_ms": 20,
            "started_at": t0.isoformat(),
            "ended_at": t1.isoformat(),
        }

        # Step 2: LLM span - response_synthesis
        t2 = datetime.now(UTC)
        await asyncio.sleep(0.03)  # Simulated LLM generation latency
        t3 = datetime.now(UTC)

        final_answer = f"Thank you for contacting customer support. Based on our policy: {matched_kb}"
        llm_span = {
            "name": "llm_response_synthesis",
            "span_type": "llm",
            "status": "completed",
            "input": {"context": matched_kb, "query": query},
            "output": {"answer": final_answer},
            "model": "gpt-4o-mini-simulated",
            "prompt_tokens": 120,
            "completion_tokens": 45,
            "total_tokens": 165,
            "cost_usd": 0.00045,
            "duration_ms": 30,
            "started_at": t2.isoformat(),
            "ended_at": t3.isoformat(),
        }

        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        total_tokens = 55 + 165
        total_cost = Decimal("0.000560")

        return AgentExecutionResult(
            output={"answer": final_answer, "status": "success", "query": query},
            duration_ms=duration_ms,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            spans=[kb_span, llm_span],
        )


class SupportAgentV2Improved(BaseAgentAdapter):
    """
    Improved customer support reasoning agent (v2.0-improved).
    Synthesizes polite, formatted bulleted answers with policy citations.
    """

    name = "support_agent"
    version = "2.0-improved"
    description = "Improved customer support agent with polite formatting and policy citations"

    async def execute(self, prompt_input: Any, config: dict[str, Any] | None = None) -> AgentExecutionResult:
        start_time = time.perf_counter()
        query = str(prompt_input.get("query", prompt_input) if isinstance(prompt_input, dict) else prompt_input)
        query_lower = query.lower()

        t0 = datetime.now(UTC)
        await asyncio.sleep(0.015)
        t1 = datetime.now(UTC)

        matched_kb = "No specific FAQ article found. General customer support assistance will be provided."
        for k, v in KNOWLEDGE_BASE.items():
            if k in query_lower:
                matched_kb = v
                break

        kb_span = {
            "name": "knowledge_base_search",
            "span_type": "tool",
            "status": "completed",
            "input": {"query": query},
            "output": {"result": matched_kb},
            "model": "kb-embed-v2-dense",
            "prompt_tokens": 20,
            "completion_tokens": 25,
            "total_tokens": 45,
            "cost_usd": 0.00009,
            "duration_ms": 15,
            "started_at": t0.isoformat(),
            "ended_at": t1.isoformat(),
        }

        t2 = datetime.now(UTC)
        await asyncio.sleep(0.025)
        t3 = datetime.now(UTC)

        final_answer = (
            f"Hello! Thank you for reaching out to TraceHarbor Support.\n\n"
            f"Here is the official policy regarding your inquiry:\n"
            f"• {matched_kb}\n\n"
            f"Please let us know if you need any additional help!"
        )

        llm_span = {
            "name": "llm_response_synthesis",
            "span_type": "llm",
            "status": "completed",
            "input": {"context": matched_kb, "query": query},
            "output": {"answer": final_answer},
            "model": "gpt-4o-mini-simulated",
            "prompt_tokens": 110,
            "completion_tokens": 55,
            "total_tokens": 165,
            "cost_usd": 0.00042,
            "duration_ms": 25,
            "started_at": t2.isoformat(),
            "ended_at": t3.isoformat(),
        }

        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        total_tokens = 45 + 165
        total_cost = Decimal("0.000510")

        return AgentExecutionResult(
            output={"answer": final_answer, "status": "success", "query": query},
            duration_ms=duration_ms,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            spans=[kb_span, llm_span],
        )


class SupportAgentV09Buggy(BaseAgentAdapter):
    """
    Baseline or legacy buggy support agent (v0.9-buggy).
    Has a known defect: misinterprets return policy as 14 days instead of 30 days,
    and fails on warranty queries. Used to test regression detection.
    """

    name = "support_agent"
    version = "0.9-buggy"
    description = "Legacy agent with outdated 14-day policy defect for regression testing"

    async def execute(self, prompt_input: Any, config: dict[str, Any] | None = None) -> AgentExecutionResult:
        start_time = time.perf_counter()
        query = str(prompt_input.get("query", prompt_input) if isinstance(prompt_input, dict) else prompt_input)
        query_lower = query.lower()

        t0 = datetime.now(UTC)
        await asyncio.sleep(0.03)
        t1 = datetime.now(UTC)

        # Defect: reports 14 days return policy instead of 30 days
        if "return" in query_lower or "policy" in query_lower:
            matched_kb = "Returns are accepted strictly within 14 days of purchase."
        elif "warranty" in query_lower:
            # Defect: misses warranty
            matched_kb = "Warranty information is currently unavailable."
        else:
            matched_kb = KNOWLEDGE_BASE.get("shipping", "General assistance.")

        kb_span = {
            "name": "knowledge_base_search",
            "span_type": "tool",
            "status": "completed",
            "input": {"query": query},
            "output": {"result": matched_kb},
            "model": "kb-legacy-v0",
            "prompt_tokens": 30,
            "completion_tokens": 30,
            "total_tokens": 60,
            "cost_usd": 0.00015,
            "duration_ms": 30,
            "started_at": t0.isoformat(),
            "ended_at": t1.isoformat(),
        }

        final_answer = f"Legacy Notice: {matched_kb}"
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))

        return AgentExecutionResult(
            output={"answer": final_answer, "status": "success", "query": query},
            duration_ms=duration_ms,
            total_tokens=60,
            total_cost_usd=Decimal("0.000150"),
            spans=[kb_span],
        )


class AgentRegistry:
    """
    Registry of approved agents and versions.
    Rejects unauthorized or unregistered execution targets.
    """

    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], BaseAgentAdapter] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(SupportAgentV1())
        self.register(SupportAgentV2Improved())
        self.register(SupportAgentV09Buggy())

    def register(self, adapter: BaseAgentAdapter) -> None:
        self._adapters[(adapter.name.lower(), adapter.version.lower())] = adapter

    def get(self, name: str, version: str) -> BaseAgentAdapter | None:
        return self._adapters.get((name.lower().strip(), version.lower().strip()))

    def list_approved_agents(self) -> list[dict[str, Any]]:
        """Return directory of approved agents for UI selection and validation."""
        return [
            {
                "agent_name": adapter.name,
                "agent_version": adapter.version,
                "description": adapter.description,
            }
            for adapter in self._adapters.values()
        ]


agent_registry = AgentRegistry()
