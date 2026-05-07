"""
Travel Concierge — 3-Agent Demo (CrewAI + Gemini + NeatLogs)
=============================================================

Pattern mirrors meeting-action-agent (src/telemetry.py + crew.py):
  1. `load_dotenv()` first.
  2. `observability.trace_utils.init()` runs BEFORE importing crewai /
     google.genai so auto-instrumentation patches land.
  3. The full crew run is wrapped in a single WORKFLOW span via `@neatlogs.span(...)`.
  4. Static demo artifacts (tables, images, detections) are emitted as
     structured `neatlogs.log(...)` events on the active WORKFLOW span — NOT
     as fake CHAIN spans. This avoids noisy / empty "see more" rows in the UI.
  5. Script ends with `neatlogs.flush()`.
"""

import base64
import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

# Init NeatLogs FIRST — before crewai / google.genai imports.
from observability.trace_utils import init as _telemetry_init, flush as _telemetry_flush  # noqa: E402
_TRACING = _telemetry_init(tags=["3-agent-demo", "investor-demo"])

# NOW import crewai + google.genai (auto-instrumented from here on).
import neatlogs  # noqa: E402
from crewai import Agent, Task, Crew, Process  # noqa: E402
from crewai.tools import tool  # noqa: E402

# google.genai client is NOT required for this demo (CrewAI routes via LiteLLM)
# — keep import lazy/optional.
try:
    import google.genai as genai  # noqa: F401
except ImportError:
    genai = None

MODEL = "gemini-2.5-flash"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _emit_artifact(
    label: str,
    category: str,
    agent: str,
    body: str,
    **metadata,
) -> None:
    """Emit a non-LLM artifact (table, image, detection, etc.) as a structured
    `neatlogs.log(...)` event on the currently-active span (the WORKFLOW).

    These artifacts are static demo data, not actual runtime operations, so they
    don't warrant their own span rows in the UI. Logging them keeps the data
    searchable on the parent trace without cluttering the span tree.
    """
    try:
        flat_metadata = {
            k: v if isinstance(v, (str, int, float, bool))
            else json.dumps(v, default=str)[:2000]
            for k, v in metadata.items()
        }
        neatlogs.log(
            "[artifact] {category}: {label}",
            category=category,
            label=label,
            agent=agent,
            body=body[:2000],
            **flat_metadata,
        )
    except Exception:
        pass
    print(f"  ◉  {category:12s} {label[:60]}")


def fetch_b64(url: str) -> str:
    try:
        r = httpx.get(url, timeout=8, follow_redirects=True)
        return base64.b64encode(r.content).decode()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Tools (CrewAI @tool → auto-captured as TOOL spans by the CrewAI instrumentor)
# ─────────────────────────────────────────────────────────────────────────────

@tool("search_flights")
def search_flights(origin: str, destination: str) -> str:
    """Search available flights between two cities."""
    time.sleep(0.2)
    return json.dumps([
        {"airline": "Singapore Airlines", "flight": "SQ35+SQ947", "route": "SFO→SIN→DPS", "duration": "19h 35m", "price_usd": 1280, "on_time_pct": "91%", "url": "https://www.singaporeair.com"},
        {"airline": "Cathay Pacific", "flight": "CX879+CX711", "route": "SFO→HKG→DPS", "duration": "21h 35m", "price_usd": 1095, "on_time_pct": "87%", "url": "https://www.cathaypacific.com"},
        {"airline": "Japan Airlines", "flight": "JL001+JL725", "route": "SFO→NRT→DPS", "duration": "23h 15m", "price_usd": 1410, "on_time_pct": "94%", "url": "https://www.jal.com"},
    ])


@tool("compare_flights")
def compare_flights(flight_data: str) -> str:
    """Compare flight options and return the best pick with reasoning."""
    time.sleep(0.15)
    return json.dumps({
        "winner": "Singapore Airlines SQ35+SQ947",
        "reasoning": "Best price/duration. 91% on-time, 19h 35m, $1,280 — leaves strong budget room for a $4k trip.",
        "savings_vs_jal": 130,
    })


@tool("search_hotels")
def search_hotels(destination: str, vibe: str) -> str:
    """Search for hotels matching a destination and vibe."""
    time.sleep(0.25)
    b64_alila = fetch_b64("https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600")
    b64_karma = fetch_b64("https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600")
    return json.dumps([
        {"name": "Alila Villas Uluwatu", "price_night": 650, "total_7n": 4550, "rating": 4.9, "vibe": "Clifftop luxury, infinity pools over Indian Ocean, adults-only", "url": "https://www.alilahotels.com/uluwatu", "image": {"url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600", "base64": b64_alila, "caption": "Alila Villas — infinity pool at sunset"}},
        {"name": "Karma Kandara", "price_night": 480, "total_7n": 3360, "rating": 4.8, "vibe": "Bohemian clifftop, private beach by cable car, Balinese art", "url": "https://www.karma-group.com/karma-kandara", "image": {"url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600", "base64": b64_karma, "caption": "Karma Kandara — clifftop villa pool"}},
    ])


@tool("check_budget")
def check_budget(hotel_price_night: float, flight_price: float, nights: int) -> str:
    """Calculate full trip cost and check against stated budget."""
    time.sleep(0.1)
    accommodation = hotel_price_night * nights
    total = accommodation + flight_price + 595 + 420 + 280 + 415
    return json.dumps({
        "accommodation": accommodation, "flights": flight_price,
        "food_7d": 595, "activities": 420, "transport": 280, "misc": 415,
        "total_estimated": total, "stated_budget": 4000,
        "over_by": round(total - 4000, 0),
        "verdict": "Over budget" if total > 4000 else "Within budget",
    })


@tool("audit_recommendations")
def audit_recommendations(places: str) -> str:
    """Audit recommendations for tourist traps or quality issues."""
    time.sleep(0.1)
    return json.dumps({
        "Single Fin Beach Club": {"tourist_index": 7.2, "verdict": "Iconic but crowded on Sundays — go midweek"},
        "Alila Villas Uluwatu": {"review_authenticity": "verified", "verdict": "Authentic reviews, safe to book"},
        "Kecak Fire Dance": {"tourist_index": 9.4, "verdict": "Skip — very touristy, over-commercialised"},
    })


# ─────────────────────────────────────────────────────────────────────────────
# Agents (CrewAI auto-instrumentation emits an AGENT span per execution)
# ─────────────────────────────────────────────────────────────────────────────

flight_agent = Agent(
    role="Flight Intelligence Specialist",
    goal="Find the best SFO→Bali flights for a $4k budget trip. Recommend clearly with reasoning.",
    backstory="You are Aria — a flight expert who finds the perfect flight balancing price, comfort, and timing. Always explain why you recommend what you recommend.",
    tools=[search_flights, compare_flights],
    llm=f"gemini/{MODEL}",
    verbose=True,
    max_iter=2,
)

hotel_agent = Agent(
    role="Luxury Hotel Scout",
    goal="Find top 2 hotels in Uluwatu matching aesthetic/wellness vibes. Be honest about budget impact.",
    backstory="You are Marco — a hotel scout who matches traveller vibe to property soul. Always flag budget concerns honestly.",
    tools=[search_hotels, check_budget],
    llm=f"gemini/{MODEL}",
    verbose=True,
    max_iter=2,
)

trust_agent = Agent(
    role="Trust & Quality Analyst",
    goal="Audit all recommendations for tourist traps, budget overruns, quality issues. Write in plain human language.",
    backstory="You are Iris — a sharp travel analyst who protects travellers from disappointment. Flag risks clearly, confirm what's trustworthy.",
    tools=[audit_recommendations],
    llm=f"gemini/{MODEL}",
    verbose=True,
    max_iter=2,
)

# ─────────────────────────────────────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────────────────────────────────────

flight_task = Task(
    description="Search SFO→DPS flights Jun 1–8 2025 using search_flights, then compare_flights. Budget: $4k total trip. Return best airline, price, and reasoning.",
    expected_output="Best flight pick with airline, price, duration, and clear reasoning.",
    agent=flight_agent,
)

hotel_task = Task(
    description="Search Uluwatu hotels (aesthetic, wellness, clifftop) using search_hotels. Then check_budget with hotel_price_night=650, flight_price=1280, nights=7. Return top picks with honest budget analysis.",
    expected_output="Top 2 hotel picks with prices, vibes, and honest budget impact.",
    agent=hotel_agent,
)

trust_task = Task(
    description="Use audit_recommendations with places='Single Fin Beach Club, Alila Villas Uluwatu, Kecak Fire Dance'. Write 3 plain-language detections: budget warning, tourist trap, positive verification.",
    expected_output="3 human-readable detections: 1 high budget warning, 1 tourist trap flag, 1 positive confirmation.",
    agent=trust_agent,
)

# ─────────────────────────────────────────────────────────────────────────────
# Crew kickoff wrapped in a top-level WORKFLOW span
# ─────────────────────────────────────────────────────────────────────────────

crew = Crew(
    agents=[flight_agent, hotel_agent, trust_agent],
    tasks=[flight_task, hotel_task, trust_task],
    process=Process.sequential,
    verbose=True,
)


@neatlogs.span(kind="WORKFLOW", name="travel-concierge.3-agent-demo")
def run_demo():
    print("\n" + "=" * 60)
    print("  🌴  TRAVEL CONCIERGE — 3-Agent Demo")
    print("  CrewAI + Gemini 2.5 Flash + NeatLogs")
    endpoint = os.environ.get("NEATLOGS_ENDPOINT") or "https://staging-cloud.neatlogs.com"
    print(f"  Endpoint: {endpoint}")
    print("=" * 60 + "\n")

    result = crew.kickoff(
        inputs={"destination": "Bali", "budget": 4000, "origin": "San Francisco"}
    )

    # ── Extra artifact spans (CHAIN spans with structured metadata) ──────────
    print("\n  Emitting artifact spans...")

    _emit_artifact(
        label="Flight Comparison Table",
        category="table",
        agent="Flight Intelligence Specialist",
        body=(
            "| Airline | Route | Duration | Price | On-Time |\n"
            "|---|---|---|---|---|\n"
            "| Singapore Airlines | SFO→SIN→DPS | 19h 35m | $1,280 | 91% |\n"
            "| Cathay Pacific | SFO→HKG→DPS | 21h 35m | $1,095 | 87% |\n"
            "| Japan Airlines | SFO→NRT→DPS | 23h 15m | $1,410 | 94% |"
        ),
    )

    for label, url, caption in [
        ("Alila Villas Uluwatu", "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600", "Alila Villas — infinity pool over the Indian Ocean"),
        ("Karma Kandara", "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600", "Karma Kandara — clifftop villa, Bali"),
        ("Uluwatu Cliffs", "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=600", "Uluwatu coastline at golden hour"),
    ]:
        b64 = fetch_b64(url)
        _emit_artifact(
            label=f"Image: {label}",
            category="image",
            agent="Luxury Hotel Scout",
            body=caption,
            image_url=url,
            mime_type="image/jpeg",
            # Base64 payloads can get large — truncate heavily on the span
            base64_size=len(b64),
        )
        print(f"  🖼  {caption}")

    _emit_artifact(
        label="Hotel Comparison Table",
        category="table",
        agent="Luxury Hotel Scout",
        body=(
            "| Hotel | $/night | 7-night total | Rating | Vibe |\n"
            "|---|---|---|---|---|\n"
            "| Alila Villas Uluwatu | $650 | $4,550 | ⭐ 4.9 | Clifftop luxury, adults-only |\n"
            "| Karma Kandara | $480 | $3,360 | ⭐ 4.8 | Bohemian, private beach by cable car |"
        ),
    )

    _emit_artifact(
        label="Budget Breakdown",
        category="table",
        agent="Luxury Hotel Scout",
        body=(
            "| Category | Cost |\n"
            "|---|---|\n"
            "| Flights (SQ) | $1,280 |\n"
            "| Hotel Alila 7N | $4,550 |\n"
            "| Food & Dining | $595 |\n"
            "| Activities | $420 |\n"
            "| Transport | $280 |\n"
            "| Misc | $415 |\n"
            "| **Total** | **$7,540** |\n"
            "| Your Budget | $4,000 |\n"
            "| Over by | **$3,540** |\n\n"
            "⚠️ Switch to Karma Kandara ($480/night) to save $1,190."
        ),
    )

    detections = [
        ("DET-001", "high", "Hotel Alone Blows the Entire Budget",
         "Alila Villas at $650/night × 7 = $4,550 — more than your whole $4,000 budget before flights or food. Total trip is ~$7,500.",
         "Accommodation: $4,550. Flight: $1,280. Food+activities: ~$1,710. Total: $7,540 vs $4,000 budget.",
         "Switch to Karma Kandara ($480/night) — saves $1,190, still clifftop luxury with a private beach."),
        ("DET-002", "medium", "Single Fin Sundays Is Now a Tourist Event",
         "Sunday Sessions now draws 400+ people and tourist buses. Worth going — but it's no longer intimate.",
         "7,000+ Instagram tags/week. TikTok: 2.8M views. Tour operators run scheduled shuttles.",
         "Go Tuesday or Wednesday — same cliffs and cocktails, fraction of the crowd."),
        ("DET-003", "info", "✅ Alila Villas Reviews Are Verified Authentic",
         "Alila has 9.4/10 from 2,841 reviews with no fake patterns. Consistent and genuine. Safe to book.",
         "Healthy distribution. 82% of reviews within 12 months. No rating spikes or bot clusters.",
         "No action needed — book with confidence."),
    ]
    for det_id, severity, title, message, evidence, rec in detections:
        _emit_artifact(
            label=f"Detection: {title}",
            category="detection",
            agent="Trust & Quality Analyst",
            body=f"[{severity.upper()}] {title}\n\n{message}",
            detection_id=det_id,
            severity=severity,
            title=title,
            message=message,
            evidence=evidence,
            recommendation=rec,
        )
        icon = {"high": "🔴", "medium": "🟡", "info": "🟢"}.get(severity, "⚪")
        print(f"  {icon}  [{severity.upper()}] {title}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

try:
    run_demo()
finally:
    print("\n  Flushing spans...")
    _telemetry_flush()

    endpoint = os.environ.get("NEATLOGS_ENDPOINT") or "https://staging-cloud.neatlogs.com"
    print("\n" + "=" * 60)
    print(f"  ✅  Done — check {endpoint}")
    print("=" * 60)
