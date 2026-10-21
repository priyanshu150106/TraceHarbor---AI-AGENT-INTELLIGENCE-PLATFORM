"""
TraceHarbor Demo Agent — Customer Support Reasoning Agent

A deterministic reference agent demonstrating the TraceHarbor Python SDK.
Executes multi-step reasoning, nested tool calling, error recording,
and token/cost metadata tracking without requiring third-party LLM API keys.

Usage:
    python demo-agents/support_agent.py
    python demo-agents/support_agent.py --query "What is the return policy?"
    python demo-agents/support_agent.py --simulate-error
"""

import argparse
import sys
import time
from typing import Any

import traceharbor

# Sample local deterministic knowledge base
KNOWLEDGE_BASE = {
    "return policy": "Customers can return items within 30 days of purchase for a full refund or exchange.",
    "shipping time": "Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days.",
    "warranty": "All electronic devices include a standard 1-year limited hardware warranty.",
}


def lookup_knowledge_base(query: str, simulate_error: bool = False) -> str:
    """
    Simulated tool: searches the internal knowledge base.
    Instrumented with traceharbor.span(span_type='tool').
    """
    with traceharbor.span("knowledge_base_search", span_type="tool") as s:
        s.set_input({"query": query, "simulate_error": simulate_error})
        s.set_metadata({"tool_version": "1.0", "index": "customer_faq"})

        time.sleep(0.05)  # Simulate brief I/O latency

        if simulate_error:
            err = ConnectionError("Knowledge base service unreachable (simulated error)")
            s.set_error(err)
            raise err

        query_lower = query.lower()
        matched = "No specific FAQ article found. General assistance will be provided."
        for key, value in KNOWLEDGE_BASE.items():
            if key in query_lower:
                matched = value
                break

        s.set_output({"result": matched})
        s.set_tokens(prompt=25, completion=30, total=55, cost_usd=0.00011, model="kb-embed-v1")
        return matched


@traceharbor.trace(name="support_agent", version="1.0", tags=["demo", "support", "faq"])
def run_support_agent(user_query: str, simulate_error: bool = False) -> dict[str, Any]:
    """
    Top-level agent workflow function.
    Automatically captured as an execution Run and root Span.
    """
    print(f"\n[TraceHarbor Agent] Received Question: '{user_query}'")

    # Step 1: Query analysis & tool invocation
    kb_result: str = ""
    error_occurred = False
    try:
        print("[TraceHarbor Agent] Executing tool: knowledge_base_search...")
        kb_result = lookup_knowledge_base(user_query, simulate_error=simulate_error)
        print(f"[TraceHarbor Agent] Knowledge retrieved: {kb_result}")
    except ConnectionError as e:
        print(f"[TraceHarbor Agent] Tool Error caught: {e}")
        error_occurred = True
        kb_result = "Apologies, our internal knowledge base is temporarily unreachable."

    # Step 2: Simulated LLM answer synthesis
    with traceharbor.span("llm_response_synthesis", span_type="llm") as s:
        s.set_input({"context": kb_result, "query": user_query})
        s.set_metadata({"temperature": 0.3})

        time.sleep(0.08)  # Simulate LLM generation latency

        if error_occurred:
            final_answer = "I apologize, but I am currently unable to access our policy records. A human representative will assist you."
        else:
            final_answer = f"Thank you for asking. Based on our policy: {kb_result}"

        s.set_output({"answer": final_answer})
        s.set_tokens(prompt=120, completion=45, total=165, cost_usd=0.00045, model="gpt-4o-mini-simulated")

    print(f"[TraceHarbor Agent] Final Answer: '{final_answer}'\n")

    return {
        "status": "partial_error" if error_occurred else "success",
        "query": user_query,
        "answer": final_answer,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="TraceHarbor Customer Support Demo Agent")
    parser.add_argument(
        "--query",
        type=str,
        default="What is the return policy?",
        help="Customer inquiry to answer",
    )
    parser.add_argument(
        "--simulate-error",
        action="store_true",
        help="Trigger a simulated tool error to verify error telemetry capture",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://127.0.0.1:8000",
        help="TraceHarbor backend API endpoint",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="th_live_demo_agent_key_placeholder",
        help="Project API key for trace authentication",
    )
    args = parser.parse_args()

    # 1. Initialize TraceHarbor SDK
    print(f"[TraceHarbor SDK] Initializing client (endpoint: {args.endpoint})...")
    traceharbor.init(
        api_key=args.api_key,
        endpoint=args.endpoint,
        flush_interval=1.0,
    )

    # 2. Run the agent
    try:
        run_support_agent(args.query, simulate_error=args.simulate_error)
    finally:
        # 3. Explicitly flush buffered spans before exit
        print("[TraceHarbor SDK] Flushing trace telemetry to backend...")
        traceharbor.flush(timeout=3.0)
        traceharbor.shutdown(timeout=2.0)
        print("[TraceHarbor SDK] Shutdown complete.")


if __name__ == "__main__":
    main()
