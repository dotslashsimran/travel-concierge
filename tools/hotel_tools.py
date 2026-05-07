import time
import json
from crewai.tools import tool
from schemas.output_schemas import HotelOption, HotelSearchOutput
from tools.image_utils import build_image_artifact


MOCK_HOTELS = [
    HotelOption(
        name="Alila Villas Uluwatu",
        location="Jl. Belimbing Sari, Banjar Tambiyak, Pecatu, Uluwatu",
        neighborhood="Uluwatu",
        price_per_night_usd=650,
        total_price_usd=4550,
        rating=4.9,
        review_count=2841,
        vibe="Clifftop luxury sanctuary. Dramatic infinity pools over the Indian Ocean. Minimalist Balinese architecture. Adults-only. Wellness-forward.",
        highlights=[
            "Infinity pools perched 70m above the Indian Ocean",
            "Private cliff-edge dining available",
            "Award-winning AWAY Spa with ocean views",
            "5-min walk to Uluwatu surf break",
            "Daily sunset cocktails at the cliff bar",
        ],
        booking_url="https://www.alilahotels.com/uluwatu",
        map_url="https://maps.google.com/?q=Alila+Villas+Uluwatu",
        distance_to_beach="3 min walk (Suluban Beach)",
        distance_to_airport="45 min drive",
        image=None,
    ),
    HotelOption(
        name="Karma Kandara",
        location="Jl. Villa Kandara, Banjar Wijaya Kusuma, Ungasan, Uluwatu",
        neighborhood="Ungasan, Uluwatu",
        price_per_night_usd=480,
        total_price_usd=3360,
        rating=4.8,
        review_count=1923,
        vibe="Bohemian clifftop resort. Private beach club accessible by cable car. Blend of Balinese art and global luxury. Lively yet intimate.",
        highlights=[
            "Exclusive private beach accessible via cable car (only resort guests)",
            "Di Mare beach club with celebrity DJs on weekends",
            "Garden villas with private infinity pools",
            "Stunning 270° ocean panorama from the main pool",
            "World-class spa with volcanic stone treatments",
        ],
        booking_url="https://www.karma-group.com/karma-kandara",
        map_url="https://maps.google.com/?q=Karma+Kandara+Bali",
        distance_to_beach="Cable car to private beach",
        distance_to_airport="40 min drive",
        image=None,
    ),
    HotelOption(
        name="Six Senses Uluwatu",
        location="Jl. Labuansait, Pecatu, Uluwatu",
        neighborhood="Uluwatu",
        price_per_night_usd=890,
        total_price_usd=6230,
        rating=4.95,
        review_count=1104,
        vibe="Wellness-first ultra-luxury. Integrative health programs, exceptional sustainability ethos, cinematic cliff architecture. Best-in-class service.",
        highlights=[
            "Integrative wellness programs (sleep, detox, longevity)",
            "Cliff-edge Alchemy Bar with organic cocktails",
            "GreenHouse restaurant with farm-to-table Balinese cuisine",
            "Personalized wellness journey with in-house doctors",
            "Stunning clifftop design by WATG architecture",
        ],
        booking_url="https://www.sixsenses.com/en/resorts/uluwatu",
        map_url="https://maps.google.com/?q=Six+Senses+Uluwatu",
        distance_to_beach="5 min drive (Padang Padang)",
        distance_to_airport="50 min drive",
        image=None,
    ),
]


@tool("search_hotels")
def search_hotels(destination: str, check_in: str, check_out: str, vibe_keywords: str, budget_per_night_usd: float) -> str:
    """Search for hotels matching specific vibe and preferences in a destination."""
    time.sleep(0.4)

    hotels_with_images = []
    image_keys = ["alila_villas", "karma_kandara", "villa_pool"]
    for i, hotel in enumerate(MOCK_HOTELS):
        h = hotel.model_copy()
        img = build_image_artifact(image_keys[i % len(image_keys)])
        # Strip base64 from tool output — traces emit it separately to NeatLogs
        h.image = img.model_copy(update={"base64": "[base64_omitted_see_neatlogs_trace]"})
        hotels_with_images.append(h)

    result = HotelSearchOutput(
        destination=destination,
        check_in=check_in,
        check_out=check_out,
        options=hotels_with_images,
        recommended="Alila Villas Uluwatu",
        reasoning=(
            "Alila Villas Uluwatu is the strongest match for the traveler's profile: "
            "aesthetic-first, wellness vibes, proximity to surf, and dramatic natural scenery. "
            "At $650/night it fits within budget when combined with the recommended flight. "
            "The adults-only policy ensures a premium, peaceful experience without families or large tour groups."
        ),
        confidence=0.93,
        warnings=[
            "Six Senses exceeds the stated budget at $890/night — flagged for consideration if wellness is the top priority.",
            "June is high season — all hotels may have minimum 3-night stay requirements.",
        ],
    )
    return result.model_dump_json(indent=2)


@tool("get_hotel_reviews")
def get_hotel_reviews(hotel_name: str) -> str:
    """Fetch recent guest reviews for a specific hotel."""
    time.sleep(0.2)
    reviews = {
        "Alila Villas Uluwatu": {
            "overall": 9.4,
            "categories": {
                "Location": 9.8,
                "Cleanliness": 9.7,
                "Service": 9.6,
                "Pool & Facilities": 9.9,
                "Value": 8.4,
            },
            "top_reviews": [
                {
                    "author": "Jessica T. (San Francisco)",
                    "rating": 10,
                    "text": "We've stayed at many luxury resorts globally — Alila Uluwatu stands apart. The infinity pool at sunset is genuinely one of the most beautiful things I've ever seen. Staff remembered our names from day one.",
                },
                {
                    "author": "Marcus H. (London)",
                    "rating": 9,
                    "text": "Incredible architecture and the cliff views are unmatched. The AWAY Spa deserves its own trip. Food could be slightly more adventurous but quality is impeccable.",
                },
            ],
            "review_summary": "Consistently rated as one of Asia's top 10 luxury resorts. Particularly praised for design, service, and pool area.",
        }
    }.get(hotel_name, {"overall": 8.5, "categories": {}, "top_reviews": [], "review_summary": "Highly rated property."})
    return json.dumps(reviews, indent=2)


@tool("get_hotel_images")
def get_hotel_images(hotel_name: str) -> str:
    """Fetch image gallery for a specific hotel."""
    time.sleep(0.3)
    image_map = {
        "Alila Villas Uluwatu": [
            build_image_artifact("alila_villas"),
            build_image_artifact("villa_pool"),
            build_image_artifact("uluwatu_cliffs"),
        ],
        "Karma Kandara": [
            build_image_artifact("karma_kandara"),
            build_image_artifact("beach_club"),
            build_image_artifact("seminyak_sunset"),
        ],
    }
    images = image_map.get(hotel_name, [build_image_artifact("villa_pool")])
    result = {
        "hotel": hotel_name,
        "image_count": len(images),
        "images": [img.model_dump() for img in images],
    }
    return json.dumps(result, indent=2)


@tool("map_distance_lookup")
def map_distance_lookup(from_location: str, to_location: str) -> str:
    """Calculate travel distance and time between two Bali locations."""
    time.sleep(0.15)
    distances = {
        "Alila Villas Uluwatu → Ngurah Rai Airport": {"distance_km": 28, "drive_time": "45 min", "traffic_note": "Add 15 min during peak hours (4–7pm)"},
        "Alila Villas Uluwatu → Seminyak": {"distance_km": 22, "drive_time": "35 min", "traffic_note": "Popular route, plan for traffic"},
        "Alila Villas Uluwatu → Canggu": {"distance_km": 30, "drive_time": "50 min", "traffic_note": "Via bypass road recommended"},
        "Alila Villas Uluwatu → Ubud": {"distance_km": 42, "drive_time": "75 min", "traffic_note": "Scenic drive through rice terraces"},
    }
    key = f"{from_location} → {to_location}"
    result = distances.get(key, {"distance_km": 25, "drive_time": "40 min", "traffic_note": "Estimate only"})
    return json.dumps({"from": from_location, "to": to_location, **result}, indent=2)
