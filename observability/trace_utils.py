"""
Neatlogs observability — initialised once at startup, before any LLM imports.

Traces everything automatically:
  - Every Gemini call (via google_genai instrumentation)
  - Every CrewAI agent execution and task
  - Every tool call (auto-captured by the CrewAI instrumentor)

CrewAI 1.14.1 uses its native GeminiCompletion provider (google-genai SDK),
NOT LiteLLM — so no litellm dependency or instrumentation is needed.

Each pipeline run becomes one WORKFLOW span containing:
  N AGENT spans -> each with M LLM child spans + timing
  tool calls wired in as children of the agent spans
"""

import os


_BASE_TAGS = ["travel-concierge", "bali-demo", "crewai", "gemini"]


def init(tags: list[str] | None = None) -> bool:
    """
    Initialise neatlogs. Returns True if tracing is active, False if skipped.
    Called from main.py before any crew/agent imports.
    Optionally accepts run-specific tags; falls back to base tags.
    """
    api_key = os.getenv("NEATLOGS_API_KEY", "")
    endpoint = os.getenv("NEATLOGS_ENDPOINT", "")

    if not api_key or not endpoint:
        return False

    import logging
    import neatlogs

    for logger in ("neatlogs", "urllib3", "httpcore", "asyncio"):
        logging.getLogger(logger).setLevel(logging.CRITICAL)

    neatlogs.init(
        api_key=api_key,
        endpoint=endpoint,
        workflow_name="Travel Concierge",
        instrumentations=["crewai", "google_genai"],
        tags=_BASE_TAGS + (tags or []),
        debug=True,
    )
    return True


def retag(tags: list[str]) -> None:
    """
    Update tags for the next run. Re-inits neatlogs with new tag set.
    Call this before each crew run in a batch to keep traces relevant.
    """
    api_key = os.getenv("NEATLOGS_API_KEY", "")
    endpoint = os.getenv("NEATLOGS_ENDPOINT", "")

    if not api_key or not endpoint:
        return

    import logging
    import neatlogs

    logging.getLogger("neatlogs").setLevel(logging.CRITICAL)

    try:
        neatlogs.init(
            api_key=api_key,
            endpoint=endpoint,
            workflow_name="Travel Concierge",
            instrumentations=["crewai", "google_genai"],
            tags=_BASE_TAGS + tags,
            debug=True,
        )
    except Exception:
        pass


def workflow_span(func):
    """Decorator that wraps the crew run in a top-level WORKFLOW span."""
    import neatlogs
    return neatlogs.span(kind="WORKFLOW")(func)


def flush() -> None:
    """Force-send any buffered spans. Call after crew.kickoff() completes."""
    try:
        import neatlogs
        neatlogs.flush()
    except Exception:
        pass
