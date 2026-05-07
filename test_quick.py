"""
Quick smoke test — CrewAI + Gemini + NeatLogs.

Mirrors the pattern in meeting-action-agent (src/telemetry.py + crew.py):
  - `load_dotenv()` first.
  - `observability.trace_utils.init()` runs BEFORE importing crewai so the
    instrumentors land on the client libraries before they're loaded.
  - The crew run is wrapped in a WORKFLOW span via `@neatlogs.span(...)`.
  - `neatlogs.flush()` at exit.
"""

from dotenv import load_dotenv
load_dotenv()

from observability.trace_utils import init as _telemetry_init, flush as _telemetry_flush

_TRACING = _telemetry_init(tags=["quick-test"])

# Safe to import CrewAI now.
import neatlogs  # noqa: E402
from crewai import Agent, Task, Crew, Process  # noqa: E402
from crewai.tools import tool  # noqa: E402


@tool("get_weather")
def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"Sunny, 28C in {city}."


agent = Agent(
    role="Travel Advisor",
    goal="Give a one-sentence travel tip.",
    backstory="You are a concise travel advisor.",
    tools=[get_weather],
    llm="gemini/gemini-2.5-flash",
    verbose=True,
    max_iter=2,
)

task = Task(
    description="Use get_weather for Bali and give one travel tip.",
    expected_output="One sentence tip.",
    agent=agent,
)

crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)


@neatlogs.span(kind="WORKFLOW", name="quick-test.run")
def run_crew():
    return crew.kickoff()


if __name__ == "__main__":
    try:
        result = run_crew()
        print("\nResult:", result)
    finally:
        print("\nFlushing spans...")
        _telemetry_flush()
        print("Done.")
