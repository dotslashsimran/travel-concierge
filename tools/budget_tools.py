import time
import json
from crewai.tools import tool


@tool("estimate_budget")
def estimate_budget(
    destination: str,
    duration_days: int,
    hotel_name: str,
    hotel_price_per_night: float,
    flight_price: float,
    travel_style: str,
) -> str:
    """Estimate a detailed travel budget breakdown for a trip."""
    time.sleep(0.3)

    flights = flight_price
    accommodation = hotel_price_per_night * duration_days
    daily_food = 85
    food_total = daily_food * duration_days
    activities_total = 420
    transport_total = 280
    beach_clubs_spas = 380
    shopping_misc = 250
    travel_insurance = 95
    airport_transfers = 80

    total = (
        flights + accommodation + food_total + activities_total +
        transport_total + beach_clubs_spas + shopping_misc +
        travel_insurance + airport_transfers
    )

    result = {
        "destination": destination,
        "duration_days": duration_days,
        "travel_style": travel_style,
        "budget_summary": {
            "stated_budget_usd": 4000,
            "total_estimated_usd": round(total, 0),
            "variance_usd": round(total - 4000, 0),
            "variance_pct": round(((total - 4000) / 4000) * 100, 1),
            "verdict": "Slightly over budget" if total > 4000 else "Within budget",
        },
        "breakdown": [
            {
                "category": "Flights (Round Trip SFO→DPS)",
                "estimated_usd": flights,
                "notes": "Singapore Airlines Economy — best value on route",
                "percentage_of_budget": round((flights / 4000) * 100, 1),
            },
            {
                "category": "Accommodation (7 nights, Alila Villas Uluwatu)",
                "estimated_usd": accommodation,
                "notes": "$650/night — reduces total by choosing Karma Kandara ($480/night saves $1,190)",
                "percentage_of_budget": round((accommodation / 4000) * 100, 1),
            },
            {
                "category": "Food & Dining",
                "estimated_usd": food_total,
                "notes": f"~$85/day — mix of fine dining (Mozaic, Merah Putih) and local warungs",
                "percentage_of_budget": round((food_total / 4000) * 100, 1),
            },
            {
                "category": "Activities & Experiences",
                "estimated_usd": activities_total,
                "notes": "Temple tours, surf lesson, Ubud day trip, cultural shows",
                "percentage_of_budget": round((activities_total / 4000) * 100, 1),
            },
            {
                "category": "Local Transport",
                "estimated_usd": transport_total,
                "notes": "Grab rides, private driver day hire ($65/day), scooter rental",
                "percentage_of_budget": round((transport_total / 4000) * 100, 1),
            },
            {
                "category": "Beach Clubs & Wellness",
                "estimated_usd": beach_clubs_spas,
                "notes": "3x beach club day passes + 1 spa treatment at AWAY Spa",
                "percentage_of_budget": round((beach_clubs_spas / 4000) * 100, 1),
            },
            {
                "category": "Shopping & Miscellaneous",
                "estimated_usd": shopping_misc,
                "notes": "Souvenirs, forgotten items, casual purchases",
                "percentage_of_budget": round((shopping_misc / 4000) * 100, 1),
            },
            {
                "category": "Travel Insurance",
                "estimated_usd": travel_insurance,
                "notes": "World Nomads standard plan — includes adventure sports",
                "percentage_of_budget": round((travel_insurance / 4000) * 100, 1),
            },
            {
                "category": "Airport Transfers",
                "estimated_usd": airport_transfers,
                "notes": "Private car both ways (Ngurah Rai ↔ Uluwatu)",
                "percentage_of_budget": round((airport_transfers / 4000) * 100, 1),
            },
        ],
        "saving_tips": [
            "Switch to Karma Kandara ($480/night) — saves $1,190 over 7 nights while still luxury.",
            "Eat lunch at local warungs ($5–10/meal) and save fine dining for evenings only.",
            "Book a private driver for full-day Ubud trip ($65) instead of a tour ($120+).",
            "Use Grab app for all transport — consistently cheaper than negotiating with drivers.",
            "Sundays Beach Club day pass ($50) is better value than two separate cocktails at others.",
        ],
        "splurge_recommendations": [
            "One night upgrade to Alila Villa Suite ($950) for a romantic sunset experience.",
            "Mozaic tasting menu ($120/person) — the best meal of the trip.",
            "AWAY Spa 90-min ocean-view treatment ($180) — transformative experience.",
        ],
        "currency_note": "1 USD ≈ 16,150 IDR (as of June 2025). Always pay in IDR to avoid dynamic currency conversion fees.",
    }
    return json.dumps(result, indent=2)


@tool("compare_budgets")
def compare_budgets(option_a: str, option_b: str) -> str:
    """Compare two budget scenarios side by side."""
    time.sleep(0.2)
    result = {
        "comparison": {
            "Alila Villas (current)": {
                "total_usd": 5540,
                "accommodation_usd": 4550,
                "verdict": "Premium experience, slightly over $4k budget",
            },
            "Karma Kandara (alternative)": {
                "total_usd": 4350,
                "accommodation_usd": 3360,
                "verdict": "Luxury experience, close to $4k budget",
            },
        },
        "saving_by_switching": 1190,
        "recommendation": (
            "Karma Kandara brings the trip within $4k budget while still delivering luxury. "
            "The exclusive private beach accessible by cable car is a unique differentiator. "
            "However, Alila Villas' infinity pool and location are superior for the stated aesthetic preferences."
        ),
    }
    return json.dumps(result, indent=2)
