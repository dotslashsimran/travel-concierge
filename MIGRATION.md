# Travel Concierge — NeatLogs Migration (v1.2.7 → v1.2.8)

## TL;DR

The project **never successfully sent a single trace** to the NeatLogs UI in its original form. It *looked* instrumented, but every code path had a blocking bug that either crashed the SDK at import, called removed v1 APIs, or produced a dead HTTP POST. This PR fixes all of them and aligns the project with the `neatlogs==1.2.8` (PyPI) / `sdk-v3` API surface.

After the fix, a full 7-agent CrewAI run now emits **~181–189 spans** per run, all successfully exported to `https://staging-cloud.neatlogs.com/v1/traces` (OTLP).

---

## 1. What was broken — honestly, every path was broken

The original repo has three entrypoints that each reached the NeatLogs platform differently. All three were broken.

### Entrypoint 1 — `main.py` (the "demo" entrypoint)

`main.py` calls `observability.trace_utils.init_neatlogs(...)`. That module tries to:

```python
# observability/trace_utils.py line 28 (original)
from neatlogs.core import LLMTracker, current_span_id_context
```

Both `LLMTracker` and `current_span_id_context` **were removed in `neatlogs>=1.2.0`** (v3 is pure OpenTelemetry — no `LLMTracker` class anymore).

The import raises `ImportError`, the module's `except ImportError:` catches it, sets `_NEATLOGS_AVAILABLE = False`, and every helper (`init_neatlogs`, `agent_trace`, `log_tool_span`, `log_detection`, …) short-circuits to a `return` on the first line.

**Net effect**: nothing initialises, no spans exist, no HTTP traffic leaves the process.

Even if the import had worked, the code monkey-patches the tracker's internal send method to manually POST to:

```python
# observability/trace_utils.py line 42 (original)
target_url = staging_url.rstrip("/") + "/api/data/v2"
# later, line 54:
resp = requests.post(target_url, json=api_data, headers=..., timeout=10.0)
```

This `/api/data/v2` endpoint *is actually still alive on the server* (I verified with curl — it returns `201 {"status":"accepted","message":"Data accepted and queued for processing (V4 Kafka Path)"}`), but the payload shape it expected (`{"dataDump", "projectAPIKey", "externalTraceId", "timestamp"}`) is the old v1 envelope format. The back-end accepts it, but the `dataDump` being passed in would be `json.dumps(asdict(call_data))` of a now-removed `CallData` dataclass — so even if this path fired, the server-side parser would reject it as unrecognised.

**Verdict**: `main.py` targeted `/api/data/v2` in intent, but never fired a single POST because of the import crash.

### Entrypoint 2 — `run.py`

This one uses the modern `neatlogs.init(...)` call with `endpoint=os.environ["NEATLOGS_ENDPOINT"]`, which correctly routes to `https://staging-cloud.neatlogs.com/v1/traces` via the SDK's OTLP exporter.

**BUT** `run.py` then does:

```python
tracker = neatlogs.init(...)  # returns None in v3 (old code expects an LLMTracker)
# ...
s = tracker.start_llm_span(...)  # AttributeError: 'NoneType' has no attribute 'start_llm_span'
tracker.end_llm_span(s)          # same
for t in tracker._threads:       # same
```

So `init()` works, CrewAI/LiteLLM/google_genai auto-instrumentation would start emitting spans, **but the first manual `tracker.start_llm_span(...)` call at line 33 crashes the process** before most of the work happens.

**Verdict**: `run.py` would have targeted `/v1/traces` correctly, but crashed before the workflow ran.

### Entrypoint 3 — `test_quick.py`

Same pattern as `run.py`. `init()` succeeds, the CrewAI kickoff auto-instruments fine, but at the end:

```python
if tracker:
    for t in tracker._threads:   # AttributeError: 'NoneType' has no attribute '_threads'
        t.join(timeout=8)
```

**Verdict**: the quick test **may** have actually exported spans from the CrewAI kickoff (because auto-instrumentation runs before the crash), but the crash at shutdown masks any visible success and `neatlogs.shutdown()` is never called so the export buffer may be lost.

### Where does `/v1/traces` fit in?

`/v1/traces` is the standard **OpenTelemetry HTTP ingestion path**. It's appended *internally* by `neatlogs.init()` → `OTLPSpanExporter` to whatever `endpoint=` you pass. **Your code never writes `/v1/traces` literally**, and `travel-concierge`'s original code never writes it either. It's the SDK's OTLP exporter path.

The original repo used:
- `/api/data/v2` (legacy, manual POST) in `main.py` — **dead path practically, because of the `ImportError`**.
- `/v1/traces` (OTLP, SDK-managed) in `run.py` + `test_quick.py` — **would have worked except for the manual `tracker.*` calls that crash on v3**.

### Why `neatlogs==1.2.7` vs `1.2.8`?

`1.2.7` was pinned in the original `requirements.txt`. Verified: `1.2.7` has the **same** v3 shape as `1.2.8` — no `LLMTracker`, no `current_span_id_context`, `init()` returns `None`. So the bugs above apply identically on both. `1.2.8` is what we pin going forward because it's the current public release on PyPI.

---

## 2. Fixes applied in this PR

### `observability/trace_utils.py` — rewritten end-to-end

Before: 384 lines, dependent on `LLMTracker`, `current_span_id_context`, manual `requests.post` to `/api/data/v2`, ~12 custom helpers (`agent_trace`, `log_tool_span`, `log_image_artifact`, `log_detection`, `log_memory_update`, etc.).

After: 91 lines. Mirrors `meeting-action-agent-changed/src/telemetry.py` exactly:

- `init(tags=None) -> bool` — calls `neatlogs.init(api_key, endpoint, workflow_name="Travel Concierge", instrumentations=["crewai","google_genai"], tags=...)`.
- `flush()` — calls `neatlogs.flush()` and `neatlogs.shutdown()`.
- `workflow_span(func)` — thin wrapper around `@neatlogs.span(kind="WORKFLOW")`.

Also silences the noisy internal loggers (`neatlogs`, `urllib3`, `httpcore`, `asyncio`) to stop the debug log spam in demos.

No back-compatibility shims — the v1 helpers (`agent_trace`, `log_tool_span`, `log_*`) are gone. Anyone who imported them gets a clear `ImportError` instead of silent-no-ops.

### `main.py` — correct init order + workflow span

Before:
```python
from config import NEATLOGS_API_KEY, NEATLOGS_BASE_URL, GEMINI_API_KEY  # loads config w/ load_dotenv()
from observability.trace_utils import init_neatlogs
from crew.travel_crew import TravelConcierge   # ← imports CrewAI BEFORE neatlogs.init()
# ...
init_neatlogs(api_key=..., base_url=..., project_name="travel-concierge-demo")
```

**Problem**: CrewAI/LiteLLM/google.genai are imported *before* `init_neatlogs()` fires, so auto-instrumentation never patches them. Even if the SDK worked, no agent/LLM/tool spans would be captured.

After:
```python
from dotenv import load_dotenv
load_dotenv()                                           # .env FIRST
from observability.trace_utils import init as _telemetry_init, flush as _telemetry_flush
_TRACING = _telemetry_init()                            # neatlogs.init() NEXT

import neatlogs                                         # noqa: E402
from crew.travel_crew import TravelConcierge            # noqa: E402  ← CrewAI imported AFTER

@neatlogs.span(kind="WORKFLOW", name="travel-concierge.main")
def _run_pipeline(trip_request: dict) -> str:
    return TravelConcierge().run(trip_request)

def main():
    try:
        result = _run_pipeline(BALI_TRIP_REQUEST)
        ...
    finally:
        _telemetry_flush()
```

Three changes:
1. `load_dotenv()` runs first, before any other imports touch `os.environ`.
2. `neatlogs.init()` runs immediately after, before any `crewai`/`litellm`/`google.genai` import.
3. The whole trip execution is wrapped in a `@neatlogs.span(kind="WORKFLOW", name="travel-concierge.main")` so the CrewAI kickoff (which is a `CHAIN` from openinference) has a proper `WORKFLOW` parent.

### `test_quick.py` — same init pattern + workflow wrap

Uses `observability.trace_utils.init()` + `flush()`, wraps the single-agent kickoff in `@neatlogs.span(kind="WORKFLOW", name="quick-test.run")`.

### `run.py` — same init pattern + artifact events via `neatlogs.log`

Replaced the broken `tracker.start_llm_span(...)` / `tracker.end_llm_span(...)` pair with `neatlogs.log(template, **kwargs)` events emitted on the active `WORKFLOW` span — which is the correct way in v3 to attach structured log records to a span instead of creating spans for non-LLM "decorative" events.

### `crew/travel_crew.py` — major cleanup

The original file imported ~8 custom v1 helpers (`agent_trace`, `log_tool_span`, `log_image_artifact`, `log_table_artifact`, `log_url_artifact`, `log_markdown_artifact`, `log_detection`, `log_reasoning_step`, `log_memory_update`, `log_orchestration_decision`) and called them in ~30 places throughout the crew runner + `TravelConciergeCallbacks` class.

All of those:
1. Were removed from `trace_utils.py` (there's no v3-equivalent — it's not how the new SDK is supposed to be used).
2. Would have raised `ImportError` on any run with v3 SDK.
3. Were creating decorative **`artifact`-kind spans** for static demo data (hardcoded hotel lists, detection lists, budget tables) that were never real tool executions. This is an anti-pattern — the SDK spec says spans should be for actual units of work.

Replacement: a single local helper `_log_event(template, **data)` that wraps `neatlogs.log(...)`. All 30 call sites were replaced with `_log_event(...)` calls that emit structured log events on the currently-active span. These become searchable log records on the `WORKFLOW` span instead of creating junk spans.

Also removed the `TravelConciergeCallbacks` class entirely — it was only used to feed the deleted `log_*` helpers.

### `_emit_post_execution_traces()` — fixed the CrewAI tool calling convention

The function calls `search_flights(...)`, `search_hotels(...)`, `search_places(...)`, `estimate_budget(...)` — all decorated with `@tool("name")` from `crewai.tools`.

Original code:
```python
flight_raw = search_flights.run({
    "origin": "SFO", "destination": "DPS", ...
})
```

This hits `crewai.tools.base_tool.BaseTool.run()` which tries to coerce the single-dict-arg into the tool's Pydantic `args_schema`, but with modern CrewAI's `@tool` shape, `.run()` expects **keyword arguments directly**, not a dict. Original code raises:

```
TypeError: search_flights() missing 3 required positional arguments: 'destination', 'departure_date', 'return_date'
```

Fix: call the raw Python function via `.func(...)` (CrewAI `@tool` keeps the original function accessible as `.func`), which skips the Pydantic coercion entirely:

```python
flight_raw = search_flights.func(
    origin="SFO", destination="DPS",
    departure_date="June 1, 2025", return_date="June 8, 2025",
)
```

Applied to all 4 call sites (`search_flights`, `search_hotels`, `search_places`, `estimate_budget`).

### `requirements.txt`

Before: `neatlogs[crewai,google-genai,litellm]==1.2.7`, `crewai>=0.80.0` (floats widely), various unpinned libs.

After:
```
neatlogs[crewai,google-genai]==1.2.8
crewai==1.14.1
openinference-instrumentation-crewai==1.1.2
# ... rest unchanged
```

- `neatlogs==1.2.8` from PyPI, not a local editable install. Anyone cloning fresh gets the right SDK.
- `crewai==1.14.1` + `openinference-instrumentation-crewai==1.1.2` pinned — verified compatibility with the `neatlogs[crewai]` extra.
- **No `litellm` extra or standalone dep** — CrewAI 1.14.1 uses its native `GeminiCompletion` provider (backed by `google-genai` SDK) for `gemini/...` model strings, bypassing LiteLLM entirely. Verified by reading `crewai.llms.providers.gemini.completion.GeminiCompletion` source (no `litellm` imports) and by running both `test_quick.py` and the full `main.py` with `litellm` completely uninstalled — both exit 0 and emit full trace trees. The SDK's instrumentation manager gracefully logs `⏭️  Skipped: litellm (not installed)` at startup.
- `sdk-v3` branch features are the baseline; no `SystemPromptTemplate` usage (it's not exported by 1.2.8).

### `.gitignore`

Added:
```
.python-version
*.log
spans_raw_optimized.log
```

`spans_raw_optimized.log` is a 14MB local-debug dump from SDK's `console_exporter` debug mode. It was accidentally committed earlier; now properly ignored.

### `.env`

```
GEMINI_API_KEY=<real>
NEATLOGS_API_KEY=<real>
NEATLOGS_ENDPOINT=https://staging-cloud.neatlogs.com
# (local/dev creds commented out as alternatives)
```

`.env` was already in `.gitignore` — no secrets land in the repo. Verified with `rg` that no real keys appear in any tracked file. `.env.example` has only placeholder values.

---

## 3. Verification — what actually works now

| Entrypoint | Run outcome | Trace ID | Spans | UI visible |
|---|---|---|---|---|
| `test_quick.py` | exit 0 | `89a66c5bb531d3b8d6d1dfc78fbd7cb6` | 6 | ✓ |
| `main.py` (run 1) | exit 1 at `_emit_post_execution_traces` (fixed in run 2) | `aa503218f41fc0af76cf9e4e7f7dd391` | 177 exported | ✓ |
| `main.py` (run 2, `.run({...})` → `.run(**...)`) | exit 0 | `4843e8a526368a2d8bd833e252e040e0` | 161 | ✓ |
| `main.py` (run 3, `.run(**...)` → `.func(...)`) | exit 0 | `8edae50be788920945532d5817ac162d` | 181 | ✓ |
| `main.py` (run 4, different API key) | exit 0 | `02805e68ae597037a57846e372263543` | 189 | ✓ |

Endpoint for all runs: `https://staging-cloud.neatlogs.com/v1/traces` (OTLP path, SDK-managed).

### How the simplified span shape looks on the UI

Top-level `WORKFLOW` span (`travel-concierge.main`)
  → `CHAIN` (CrewAI `Crew.kickoff`)
    → 7 × `AGENT` spans (one per crew agent)
      → `LLM` spans (gemini-2.5-pro / gemini-2.5-flash auto-instrumented)
      → `TOOL` spans (`search_flights`, `search_hotels`, `search_places`, `estimate_budget`, etc.)
  → `neatlogs.log(...)` events attached for hardcoded demo artifacts (flight tables, hotel lists, detections, budget breakdown, synthesis reasoning)

No orphan spans, no root `HTTP` spans — everything has a proper `WORKFLOW` parent.

---

## 4. Push-readiness checklist

- [x] `.env` in `.gitignore` — verified
- [x] No real keys anywhere in tracked files — verified with `rg`
- [x] `spans_raw_optimized.log` + `.python-version` added to `.gitignore`
- [x] `main.py`, `test_quick.py`, `run.py` all exit 0
- [x] Traces land on NeatLogs UI with all expected spans
- [x] Code mirrors `meeting-action-agent-changed` layout (proven reference)
- [x] No `SystemPromptTemplate` / other `agent-skill-file`-branch-only APIs used
- [x] `requirements.txt` pinned to specific versions for reproducibility
- [x] `README`-facing files (`.env.example`) still have placeholder-only values

---

## 5. Summary of moved/deleted public API

| Symbol | Status | Replacement |
|---|---|---|
| `observability.trace_utils.init_neatlogs(api_key, base_url, project_name)` | **Removed** | `observability.trace_utils.init(tags=None) -> bool` |
| `observability.trace_utils.agent_trace(agent, task, purpose, model)` | **Removed** | CrewAI auto-instrumentation handles `AGENT` spans |
| `observability.trace_utils.log_tool_span(...)` | **Removed** | CrewAI auto-instrumentation handles `TOOL` spans |
| `observability.trace_utils.log_image_artifact(...)` | **Removed** | `neatlogs.log("[image] ...", url=..., base64=...)` |
| `observability.trace_utils.log_table_artifact(...)` | **Removed** | `neatlogs.log("[table] ...", headers=..., rows=...)` |
| `observability.trace_utils.log_detection(...)` | **Removed** | `neatlogs.log("[detection] ...", severity=..., title=..., ...)` |
| `observability.trace_utils.log_memory_update(...)` | **Removed** | `neatlogs.log("[memory] ...", agent=..., key=..., summary=...)` |
| `observability.trace_utils.log_reasoning_step(...)` | **Removed** | `neatlogs.log("[reasoning] ...", step=..., thought=...)` |
| `observability.trace_utils.log_orchestration_decision(...)` | **Removed** | `neatlogs.log("[orchestrator] ...", decision=..., rationale=..., next_agents=...)` |
| `crew.travel_crew.TravelConciergeCallbacks` | **Removed** | Not needed — auto-instrumentation does this |
| `search_flights.run({...})` call convention | Changed | `search_flights.func(...)` (or `search_flights.run(**...)`) |

If anyone has downstream scripts importing from `observability.trace_utils`, they'll get an explicit `ImportError` — which is the correct signal that the API changed. No silent no-ops.
