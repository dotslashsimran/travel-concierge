import time
import random
from datetime import datetime
from crewai.tools import tool
from schemas.output_schemas import FlightOption, FlightSearchOutput


MOCK_FLIGHTS = [
    FlightOption(
        airline="Singapore Airlines",
        flight_number="SQ35 + SQ947",
        departure="SFO 23:55 (Jun 1)",
        arrival="DPS 09:30+2 (Jun 3)",
        duration="19h 35m (1 stop, SIN)",
        stops=1,
        price_usd=1280,
        cabin_class="Economy",
        booking_url="https://www.singaporeair.com",
        airline_logo_url="https://upload.wikimedia.org/wikipedia/en/thumb/8/8b/Singapore_Airlines_Logo_2.svg/200px-Singapore_Airlines_Logo_2.svg.png",
        on_time_rate="91%",
        luggage_included=True,
        notes="Best overall — premium service, great seat comfort, free baggage. Stopover in Singapore allows airport lounge access.",
    ),
    FlightOption(
        airline="Cathay Pacific",
        flight_number="CX879 + CX711",
        departure="SFO 01:10 (Jun 2)",
        arrival="DPS 13:45+1 (Jun 3)",
        duration="21h 35m (1 stop, HKG)",
        stops=1,
        price_usd=1095,
        cabin_class="Economy",
        booking_url="https://www.cathaypacific.com",
        airline_logo_url="https://upload.wikimedia.org/wikipedia/en/thumb/1/1b/Cathay_Pacific_logo.svg/200px-Cathay_Pacific_logo.svg.png",
        on_time_rate="87%",
        luggage_included=True,
        notes="Good value option — reliable carrier with solid in-flight entertainment. 2h layover in Hong Kong.",
    ),
    FlightOption(
        airline="Japan Airlines",
        flight_number="JL001 + JL725",
        departure="SFO 11:00 (Jun 2)",
        arrival="DPS 07:15+1 (Jun 4)",
        duration="23h 15m (1 stop, NRT)",
        stops=1,
        price_usd=1410,
        cabin_class="Economy",
        booking_url="https://www.jal.com",
        airline_logo_url="https://upload.wikimedia.org/wikipedia/en/thumb/e/ee/Japan_Airlines_Logo_%282002%29.svg/200px-Japan_Airlines_Logo_%282002%29.svg.png",
        on_time_rate="94%",
        luggage_included=True,
        notes="Premium experience — excellent food and service, highest on-time rating. Longer layover allows optional Tokyo city visit.",
    ),
    FlightOption(
        airline="ANA",
        flight_number="NH1 + NH875",
        departure="SFO 10:45 (Jun 2)",
        arrival="DPS 06:20+1 (Jun 4)",
        duration="22h 35m (1 stop, NRT)",
        stops=1,
        price_usd=1320,
        cabin_class="Economy",
        booking_url="https://www.ana.co.jp",
        airline_logo_url="https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/All_Nippon_Airways_Logo.svg/200px-All_Nippon_Airways_Logo.svg.png",
        on_time_rate="92%",
        luggage_included=True,
        notes="Excellent carrier, slightly pricier but exceptional reliability and service quality.",
    ),
]


@tool("search_flights")
def search_flights(origin: str, destination: str, departure_date: str, return_date: str) -> str:
    """Search for available flights between two cities for given dates."""
    time.sleep(0.3)
    result = FlightSearchOutput(
        origin=origin,
        destination=destination,
        travel_dates=f"{departure_date} → {return_date}",
        options=MOCK_FLIGHTS,
        recommended="Singapore Airlines SQ35+SQ947",
        reasoning=(
            "Singapore Airlines offers the best balance of price, comfort, and service quality. "
            "The SIN stopover is short (3h) and the airline consistently ranks top for long-haul economy. "
            "At $1,280 it leaves strong budget headroom for the $4k total trip budget."
        ),
        confidence=0.91,
        warnings=[
            "June is peak Bali season — prices may increase 15-20% if booking delayed past 4 weeks.",
            "All prices are indicative and subject to real-time availability.",
        ],
    )
    return result.model_dump_json(indent=2)


@tool("compare_flights")
def compare_flights(flight_ids: str) -> str:
    """Compare two or more flight options on price, duration, and quality."""
    time.sleep(0.2)
    comparison = {
        "comparison_table": [
            {"metric": "Price (USD)", "Singapore Airlines": "$1,280", "Cathay Pacific": "$1,095", "Japan Airlines": "$1,410"},
            {"metric": "Total Duration", "Singapore Airlines": "19h 35m", "Cathay Pacific": "21h 35m", "Japan Airlines": "23h 15m"},
            {"metric": "On-Time Rate", "Singapore Airlines": "91%", "Cathay Pacific": "87%", "Japan Airlines": "94%"},
            {"metric": "Stops", "Singapore Airlines": "1 (SIN)", "Cathay Pacific": "1 (HKG)", "Japan Airlines": "1 (NRT)"},
            {"metric": "Baggage", "Singapore Airlines": "✓ Included", "Cathay Pacific": "✓ Included", "Japan Airlines": "✓ Included"},
            {"metric": "Seat Comfort", "Singapore Airlines": "★★★★★", "Cathay Pacific": "★★★★☆", "Japan Airlines": "★★★★★"},
            {"metric": "Food Quality", "Singapore Airlines": "★★★★★", "Cathay Pacific": "★★★★☆", "Japan Airlines": "★★★★★"},
        ],
        "winner": "Singapore Airlines",
        "reasoning": "Best overall score — shortest flight time, premium service, and mid-range pricing.",
    }
    import json
    return json.dumps(comparison, indent=2)


@tool("get_airline_reviews")
def get_airline_reviews(airline: str) -> str:
    """Fetch recent traveler reviews for a specific airline."""
    time.sleep(0.2)
    reviews = {
        "Singapore Airlines": {
            "overall_rating": 4.7,
            "total_reviews": 48320,
            "recent_highlights": [
                "Crew was exceptionally warm and attentive throughout the 18h flight.",
                "The Book the Cook pre-order meal was genuinely restaurant-quality.",
                "New A350 aircraft felt fresh and comfortable. Personal air vents are great.",
            ],
            "recent_concerns": [
                "Economy seat pitch slightly tight for tall passengers (>6'2\").",
            ],
            "skytrax_rating": "5-Star Airline",
        }
    }.get(airline, {"overall_rating": 4.2, "total_reviews": 12000, "recent_highlights": [], "recent_concerns": []})
    import json
    return json.dumps(reviews, indent=2)
