"""
NeatLogs trace utilities — wraps the neatlogs v1.1.x SDK.

Key facts about the SDK:
  - neatlogs.init(api_key) returns an LLMTracker
  - tracker.start_llm_span(...) / tracker.end_llm_span(span) for manual spans
  - Auto-instruments CrewAI (Crew.kickoff, Agent.execute_task) via import monitor
  - Auto-instruments LiteLLM, Google GenAI via import monitor
  - All spans include: messages, completion, token_counts, timing, parent_span_id (tree structure)
  - Data is POSTed to the NeatLogs server as dataDump JSON

We monkey-patch the server URL so traces go to the staging endpoint.
"""

import json
import time
import functools
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Optional

_tracker = None
_NEATLOGS_AVAILABLE = False

try:
    import neatlogs
    from neatlogs.core import LLMTracker, current_span_id_context
    _NEATLOGS_AVAILABLE = True
except ImportError:
    print("[TraceUtils] neatlogs not installed — traces will be logged locally only.")


def _patch_server_url(tracker: Any, staging_url: str) -> None:
    """Monkey-patch the tracker to send data to the staging endpoint instead of prod."""
    import requests
    import json
    import threading
    from dataclasses import asdict
    from datetime import datetime

    target_url = staging_url.rstrip("/") + "/api/data/v2"

    def _patched_send(call_data):
        def send_in_background():
            try:
                trace_data = asdict(call_data)
                api_data = {
                    "dataDump": json.dumps(trace_data, default=str),
                    "projectAPIKey": call_data.api_key or tracker.api_key,
                    "externalTraceId": call_data.trace_id,
                    "timestamp": datetime.now().timestamp(),
                }
                resp = requests.post(
                    target_url,
                    json=api_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                print(f"  [NeatLogs] ✓ Span sent to staging ({resp.status_code})")
            except requests.exceptions.RequestException as e:
                print(f"  [NeatLogs] Send error: {e}")
            except Exception as e:
                print(f"  [NeatLogs] Unexpected send error: {e}")

        t = threading.Thread(target=send_in_background, daemon=False)
        t.start()
        tracker._threads.append(t)

    tracker._send_data_to_server = _patched_send


def init_neatlogs(api_key: str, base_url: str, project_name: str = "travel-concierge") -> None:
    """Initialize NeatLogs SDK and patch to the staging endpoint."""
    global _tracker, _NEATLOGS_AVAILABLE
    if not _NEATLOGS_AVAILABLE:
        print(f"[NeatLogs] SDK not available — local trace logging only.")
        return
    try:
        _tracker = neatlogs.init(
            api_key=api_key,
            tags=[project_name, "bali-demo", "multi-agent"],
            debug=False,
        )
        _patch_server_url(_tracker, base_url)
        print(f"[NeatLogs] ✓ Initialized — project: {project_name}")
        print(f"[NeatLogs] ✓ Staging endpoint: {base_url}/api/data/v2")
        print(f"[NeatLogs] ✓ Session: {_tracker.session_id}")
    except Exception as e:
        print(f"[NeatLogs] Init error: {e}")


def _get_tracker():
    return _tracker


def _start_span(
    node_name: str,
    node_type: str = "tool_call",
    model: str = "custom",
    provider: str = "travel-concierge",
    framework: str = "crewai",
    messages: Optional[list] = None,
) -> Any:
    """Start a custom NeatLogs span."""
    if not _NEATLOGS_AVAILABLE or not _tracker:
        return None
    try:
        span = _tracker.start_llm_span(
            model=model,
            provider=provider,
            framework=framework,
            node_type=node_type,
            node_name=node_name,
        )
        if messages:
            span.messages = messages
        return span
    except Exception as e:
        print(f"  [NeatLogs] start_span error: {e}")
        return None


def _end_span(span: Any, completion: str = "", success: bool = True, error: Exception = None) -> None:
    """End a custom NeatLogs span."""
    if not _NEATLOGS_AVAILABLE or not _tracker or span is None:
        return
    try:
        if completion:
            span.completion = completion[:2000]
        _tracker.end_llm_span(span, success=success, error=error)
    except Exception as e:
        print(f"  [NeatLogs] end_span error: {e}")


@contextmanager
def agent_trace(agent_name: str, task_name: str, purpose: str, model: str):
    """Context manager that creates a NeatLogs agent-level span."""
    start = time.time()
    print(f"\n{'='*60}")
    print(f"  🤖  Agent : {agent_name}")
    print(f"  📋  Task  : {task_name}")
    print(f"  🎯  Goal  : {purpose[:80]}")
    print(f"  🧠  Model : {model}")
    print(f"{'='*60}")

    span = _start_span(
        node_name=f"{agent_name} — {task_name}",
        node_type="agent_execution",
        model=model,
        provider="gemini",
        framework="crewai",
        messages=[{"role": "system", "content": purpose}],
    )
    try:
        yield span
        duration_ms = int((time.time() - start) * 1000)
        _end_span(span, completion=f"Completed in {duration_ms}ms", success=True)
    except Exception as e:
        _end_span(span, success=False, error=e)
        raise
    finally:
        duration = int((time.time() - start) * 1000)
        print(f"  ✅  {agent_name} completed in {duration}ms\n")


def log_tool_span(
    agent_name: str,
    tool_name: str,
    arguments: dict,
    result_summary: str,
    duration_ms: int,
    success: bool = True,
) -> None:
    """Log a tool call as a NeatLogs span."""
    span = _start_span(
        node_name=f"Tool: {tool_name}",
        node_type="tool_call",
        model=tool_name,
        provider=agent_name,
        framework="crewai",
        messages=[{"role": "user", "content": json.dumps(arguments, default=str)[:500]}],
    )
    if span:
        span.completion = result_summary[:1000]
        _end_span(span, completion=result_summary[:1000], success=success)
    print(f"  [Tool] ⚙️  {tool_name} ({duration_ms}ms) → {result_summary[:80]}...")


def log_image_artifact(
    agent_name: str,
    label: str,
    image_url: str,
    base64_data: str,
    mime_type: str,
    caption: str,
    source: str,
) -> None:
    """Log an image artifact as a NeatLogs span with base64 payload."""
    payload = {
        "type": "image",
        "label": label,
        "caption": caption,
        "source": source,
        "imageUrl": image_url,
        "mimeType": mime_type,
        "base64": base64_data,
    }
    span = _start_span(
        node_name=f"Image: {label}",
        node_type="artifact",
        model="image_artifact",
        provider=agent_name,
        framework="crewai",
        messages=[{"role": "user", "content": caption}],
    )
    if span:
        span.completion = json.dumps({k: v for k, v in payload.items() if k != "base64"})
        _end_span(span, completion=span.completion, success=True)
    print(f"  [Artifact] 🖼  {label}: {caption}")


def log_table_artifact(
    agent_name: str,
    label: str,
    headers: list[str],
    rows: list[list],
    caption: str = "",
) -> None:
    """Log a table artifact as a NeatLogs span."""
    table_md = _rows_to_markdown(headers, rows)
    span = _start_span(
        node_name=f"Table: {label}",
        node_type="artifact",
        model="table_artifact",
        provider=agent_name,
        framework="crewai",
        messages=[{"role": "user", "content": caption or label}],
    )
    if span:
        span.completion = table_md
        _end_span(span, completion=table_md, success=True)
    print(f"  [Artifact] 📊  {label} ({len(rows)} rows)")


def log_url_artifact(
    agent_name: str,
    label: str,
    url: str,
    title: str,
    description: str = "",
) -> None:
    """Log a URL artifact (for link unfurling) as a NeatLogs span."""
    content = json.dumps({"url": url, "title": title, "description": description})
    span = _start_span(
        node_name=f"URL: {title}",
        node_type="artifact",
        model="url_artifact",
        provider=agent_name,
        framework="crewai",
        messages=[{"role": "user", "content": f"URL: {url}"}],
    )
    if span:
        span.completion = content
        _end_span(span, completion=content, success=True)
    print(f"  [Artifact] 🔗  {title} → {url}")


def log_markdown_artifact(agent_name: str, label: str, content: str) -> None:
    """Log a markdown card artifact as a NeatLogs span."""
    span = _start_span(
        node_name=f"Card: {label}",
        node_type="artifact",
        model="markdown_artifact",
        provider=agent_name,
        framework="crewai",
        messages=[{"role": "user", "content": label}],
    )
    if span:
        span.completion = content[:2000]
        _end_span(span, completion=content[:2000], success=True)
    print(f"  [Artifact] 📝  {label}")


def log_detection(
    agent_name: str,
    detection_id: str,
    detection_type: str,
    severity: str,
    title: str,
    message: str,
    affected_items: list[str],
    evidence: str,
    recommendation: str,
) -> None:
    """Log a trust/quality detection as a NeatLogs span."""
    content = json.dumps({
        "id": detection_id,
        "type": detection_type,
        "severity": severity,
        "title": title,
        "message": message,
        "affected_items": affected_items,
        "evidence": evidence,
        "recommendation": recommendation,
    })
    span = _start_span(
        node_name=f"Detection: {title}",
        node_type="detection",
        model=f"detection_{severity}",
        provider=agent_name,
        framework="crewai",
        messages=[{"role": "user", "content": f"[{severity.upper()}] {title}"}],
    )
    if span:
        span.completion = content
        _end_span(span, completion=content, success=True)
    icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢" if severity == "info" else "🟠"
    print(f"  [Detection] {icon}  [{severity.upper()}] {title}")


def log_reasoning_step(
    agent_name: str,
    step: str,
    thought: str,
    decision: Optional[str] = None,
) -> None:
    """Log an intermediate reasoning step as a NeatLogs span."""
    content = json.dumps({"step": step, "thought": thought, "decision": decision})
    span = _start_span(
        node_name=f"Reasoning: {step}",
        node_type="reasoning",
        model="reasoning_step",
        provider=agent_name,
        framework="crewai",
        messages=[{"role": "system", "content": thought[:500]}],
    )
    if span:
        span.completion = decision or thought[:200]
        _end_span(span, completion=span.completion, success=True)
    print(f"  [Reasoning] 💭  [{agent_name}] {step}: {thought[:100]}...")


def log_memory_update(agent_name: str, key: str, summary: str) -> None:
    """Log a shared memory update as a NeatLogs span."""
    span = _start_span(
        node_name=f"Memory: {key}",
        node_type="memory_update",
        model="shared_memory",
        provider=agent_name,
        framework="crewai",
        messages=[{"role": "user", "content": f"Update '{key}': {summary}"}],
    )
    if span:
        span.completion = summary
        _end_span(span, completion=summary, success=True)
    print(f"  [Memory] 🧠  [{agent_name}] {key}: {summary[:80]}")


def log_orchestration_decision(decision: str, rationale: str, next_agents: list[str]) -> None:
    """Log an orchestration routing decision as a NeatLogs span."""
    content = json.dumps({"decision": decision, "rationale": rationale, "next_agents": next_agents})
    span = _start_span(
        node_name=f"Orchestration: {decision}",
        node_type="orchestration",
        model="orchestrator",
        provider="Lead Travel Intelligence Orchestrator",
        framework="crewai",
        messages=[{"role": "system", "content": rationale}],
    )
    if span:
        span.completion = f"Routing to: {', '.join(next_agents)}"
        _end_span(span, completion=span.completion, success=True)
    print(f"  [Orchestrator] 🎯  {decision} → {', '.join(next_agents)}")


def _rows_to_markdown(headers: list[str], rows: list[list]) -> str:
    """Convert table data to markdown format."""
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    data_rows = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header_row, separator] + data_rows)
