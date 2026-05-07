import os
from dotenv import load_dotenv
load_dotenv()

import neatlogs

tracker = neatlogs.init(
    api_key=os.environ["NEATLOGS_API_KEY"],
    endpoint=os.environ["NEATLOGS_ENDPOINT"],
    workflow_name="quick-test",
    instrumentations=["google-genai", "crewai"],
    tags=["quick-test"],
)

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

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
result = crew.kickoff()

print("\nResult:", result)

print("\nFlushing spans...")
if tracker:
    for t in tracker._threads:
        t.join(timeout=8)
print("Done — check", os.environ["NEATLOGS_ENDPOINT"])
