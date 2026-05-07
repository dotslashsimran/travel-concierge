"""
Travel Concierge — Multi-Agent AI System
=========================================
A production-quality orchestration system using CrewAI + Gemini + NeatLogs.

Generates visually rich execution traces for the NeatLogs AI observability platform.

Architecture:
  Orchestrator (gemini-2.5-pro)
    ├── Flight Agent      (gemini-2.5-flash) → search_flights, compare_flights
    ├── Hotel Scout       (gemini-2.5-pro)   → search_hotels, get_hotel_images
    ├── Local Vibes       (gemini-2.5-flash) → search_places, social_search
    ├── Itinerary Builder (gemini-2.5-pro)   → synthesizes all context
    ├── Budget Agent      (gemini-2.5-flash) → estimate_budget, compare_budgets
    └── Trust Agent       (gemini-2.5-pro)   → detections, quality analysis
"""

import sys

# Neatlogs must init before any LLM / CrewAI imports so auto-instrumentation
# patches land on the client libraries before they're loaded.
from dotenv import load_dotenv
load_dotenv()

from observability.trace_utils import init as _telemetry_init, flush as _telemetry_flush
_TRACING = _telemetry_init()

# Safe to import CrewAI now.
from config import NEATLOGS_BASE_URL, GEMINI_API_KEY  # noqa: E402
from crew.travel_crew import TravelConcierge  # noqa: E402
import neatlogs  # noqa: E402

BALI_TRIP_REQUEST = {
    "raw_request": (
        "I'm planning a 7-day Bali trip in June. "
        "Help me find flights from San Francisco, pick a beautiful hotel in Uluwatu, "
        "suggest cafes, beach clubs, and gyms, build a day-by-day itinerary, "
        "estimate my budget, and avoid overly touristy places. "
        "I like aesthetic places, wellness vibes, good food, and some nightlife. "
        "Budget is around $4k total."
    ),
    "destination": "Bali, Indonesia",
    "origin": "San Francisco, CA",
    "departure_date": "June 1, 2025",
    "return_date": "June 8, 2025",
    "duration_days": 7,
    "total_budget_usd": 4000,
    "vibe_keywords": ["aesthetic", "wellness", "good food", "nightlife", "not touristy"],
    "avoid": ["tourist traps", "large tour groups", "generic beach clubs"],
    "traveler_description": (
        "Taste-driven solo/couple traveler. Loves aesthetic spaces, specialty coffee, "
        "wellness activities (yoga, spa, gym), excellent food (mix of fine dining + authentic local), "
        "some nightlife (intimate bars, not mega-clubs), and surf culture. "
        "Strongly dislikes over-crowded, over-marketed, generic tourist experiences."
    ),
}


@neatlogs.span(kind="WORKFLOW", name="travel-concierge.main")
def _run_pipeline(trip_request: dict) -> str:
    concierge = TravelConcierge()
    return concierge.run(trip_request)


def main():
    print("\n" + "🌴 " * 20)
    print("  TRAVEL CONCIERGE — AI Orchestration Demo")
    print("  NeatLogs Observability Platform")
    print("🌴 " * 20 + "\n")

    if not GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY not set. Check your .env file.")
        sys.exit(1)

    if not _TRACING:
        print("⚠️  NEATLOGS_API_KEY / NEATLOGS_ENDPOINT not set — traces will not be exported.")
    else:
        print("🔌  NeatLogs observability active.")

    print("\n📋  Trip Request:")
    print(f"  Destination  : {BALI_TRIP_REQUEST['destination']}")
    print(f"  Origin       : {BALI_TRIP_REQUEST['origin']}")
    print(f"  Dates        : {BALI_TRIP_REQUEST['departure_date']} → {BALI_TRIP_REQUEST['return_date']}")
    print(f"  Budget       : ${BALI_TRIP_REQUEST['total_budget_usd']:,}")
    print(f"  Vibe         : {', '.join(BALI_TRIP_REQUEST['vibe_keywords'])}")

    try:
        result = _run_pipeline(BALI_TRIP_REQUEST)

        print("\n" + "=" * 70)
        print("  📄  FINAL TRAVEL BRIEF")
        print("=" * 70)
        print(result[:3000] + ("..." if len(result) > 3000 else ""))
        if NEATLOGS_BASE_URL:
            print("\n  🔗  View full traces at: " + NEATLOGS_BASE_URL)
    finally:
        _telemetry_flush()


if __name__ == "__main__":
    main()
