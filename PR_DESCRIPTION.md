# Fix NeatLogs integration — align with `neatlogs==1.2.8` / sdk-v3

## Why

Before this PR, `travel-concierge` **never successfully landed a trace on the NeatLogs UI**, despite looking fully instrumented.

The project was built against the legacy `neatlogs<=1.1.x` API (`LLMTracker`, `tracker.start_llm_span`, custom `/api/data/v2` POST). All of those symbols were removed when the SDK moved to OpenTelemetry (`neatlogs>=1.2.0`). On the pinned `neatlogs==1.2.7`:

- `observability/trace_utils.py` — `ImportError` at line 28 (`from neatlogs.core import LLMTracker, current_span_id_context`) → entire module silently disables tracing.
- `main.py` — imported CrewAI **before** `neatlogs.init()`, so auto-instrumentation never patches it even if it ran.
- `run.py` / `test_quick.py` — called `tracker.start_llm_span(...)` / `tracker._threads` on the `None` return value of `init()` → `AttributeError` crash.
- `crew/travel_crew.py` — ~30 call sites to removed helpers (`agent_trace`, `log_tool_span`, `log_detection`, `log_memory_update`, ...) — every one would crash on v3.
- `_emit_post_execution_traces()` — called `@tool`-decorated functions with a single dict arg `.run({...})` → `TypeError: missing required positional arguments` on modern CrewAI.

## What this PR does

Rewrites the tracing layer to mirror the known-good `meeting-action-agent-changed/src/telemetry.py` pattern (v3 / sdk-v3-compatible), and cleans up every broken call site.

### Scope

| Area | Change |
|---|---|
| `observability/trace_utils.py` | Rewritten 384 → 91 lines. Exposes only `init`, `flush`, `workflow_span`. No more `LLMTracker`, no more manual `/api/data/v2` POST, no more shims. |
| `main.py` | Fixed import order (`load_dotenv` → `neatlogs.init` → CrewAI import). Wrapped pipeline in `@neatlogs.span(kind="WORKFLOW", name="travel-concierge.main")`. |
| `test_quick.py` | Same init pattern. Wrapped kickoff in `@neatlogs.span(kind="WORKFLOW", name="quick-test.run")`. |
| `run.py` | Same init pattern. Replaced broken `tracker.start_llm_span` calls with `neatlogs.log(...)` structured events. |
| `crew/travel_crew.py` | Deleted all imports/calls to removed v1 helpers (~30 sites). Introduced local `_log_event(...)` → `neatlogs.log(...)` for demo artefacts. Removed `TravelConciergeCallbacks`. Fixed `.run({...})` → `.func(...)` on 4 CrewAI `@tool` call sites. |
| `requirements.txt` | Pinned `neatlogs[crewai,google-genai]==1.2.8`, `crewai==1.14.1`, `openinference-instrumentation-crewai==1.1.2`. Dropped `litellm` (CrewAI 1.14.1's native Gemini provider uses `google-genai` directly — no LiteLLM in the call path). Removed unpinned floats. |
| `.gitignore` | Added `spans_raw_optimized.log`, `.python-version`, `*.log`. |

Full details in [`MIGRATION.md`](./MIGRATION.md).

## Verification

End-to-end runs against `https://staging-cloud.neatlogs.com`:

| Entrypoint | Exit | Trace ID | Spans | UI |
|---|---|---|---|---|
| `test_quick.py` | 0 | `89a66c5bb531d3b8d6d1dfc78fbd7cb6` | 6 | ✓ |
| `main.py` | 0 | `8edae50be788920945532d5817ac162d` | 181 | ✓ |
| `main.py` (2nd key) | 0 | `02805e68ae597037a57846e372263543` | 189 | ✓ |

Span shape on UI: `WORKFLOW` (`travel-concierge.main`) → `CHAIN` (`Crew.kickoff`) → 7 × `AGENT` → `LLM` + `TOOL` spans, with `neatlogs.log(...)` events attached for demo artefacts. No orphan / root-HTTP spans.

## Backwards compatibility

Breaking — the v1 helper surface (`init_neatlogs`, `agent_trace`, `log_tool_span`, `log_image_artifact`, `log_detection`, `log_memory_update`, `log_reasoning_step`, `log_orchestration_decision`, `TravelConciergeCallbacks`) is gone. Downstream scripts will get an explicit `ImportError` — which is the correct signal that the API changed. The old surface never actually worked with `neatlogs>=1.2.0` anyway, so no one had working code depending on it.

## Security

- `.env` is in `.gitignore` (unchanged).
- Verified no API keys in any tracked file via `rg 'NEATLOGS_API_KEY=[A-Za-z0-9_-]{10,}'` etc. — only placeholders in `.env.example`.
- Local debug dumps (`spans_raw_optimized.log`) now git-ignored.

## Test plan

1. Clone fresh, `cp .env.example .env`, fill `GEMINI_API_KEY` + `NEATLOGS_API_KEY` + `NEATLOGS_ENDPOINT`.
2. `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
3. `python test_quick.py` → exit 0, trace visible on UI with ~6 spans.
4. `python main.py` → exit 0, trace visible on UI with ~180 spans, full 7-agent shape.
