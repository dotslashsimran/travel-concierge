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
import json
from config import NEATLOGS_API_KEY, NEATLOGS_BASE_URL, GEMINI_API_KEY
from observability.trace_utils import init_neatlogs
from crew.travel_crew import TravelConcierge

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


def main():
    print("\n" + "🌴 " * 20)
    print("  TRAVEL CONCIERGE — AI Orchestration Demo")
    print("  NeatLogs Observability Platform")
    print("🌴 " * 20 + "\n")

    if not GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY not set. Check your .env file.")
        sys.exit(1)

    if not NEATLOGS_API_KEY:
        print("⚠️  WARNING: NEATLOGS_API_KEY not set — traces will be logged locally only.")

    print("🔌  Initializing NeatLogs observability...")
    init_neatlogs(
        api_key=NEATLOGS_API_KEY or "",
        base_url=NEATLOGS_BASE_URL,
        project_name="travel-concierge-demo",
    )

    print("\n📋  Trip Request:")
    print(f"  Destination  : {BALI_TRIP_REQUEST['destination']}")
    print(f"  Origin       : {BALI_TRIP_REQUEST['origin']}")
    print(f"  Dates        : {BALI_TRIP_REQUEST['departure_date']} → {BALI_TRIP_REQUEST['return_date']}")
    print(f"  Budget       : ${BALI_TRIP_REQUEST['total_budget_usd']:,}")
    print(f"  Vibe         : {', '.join(BALI_TRIP_REQUEST['vibe_keywords'])}")

    concierge = TravelConcierge()
    result = concierge.run(BALI_TRIP_REQUEST)

    print("\n" + "="*70)
    print("  📄  FINAL TRAVEL BRIEF")
    print("="*70)
    print(result[:3000] + ("..." if len(result) > 3000 else ""))
    print("\n  🔗  View full traces at: " + NEATLOGS_BASE_URL)


if __name__ == "__main__":
    main()
