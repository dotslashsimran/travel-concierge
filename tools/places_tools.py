import time
import json
from crewai.tools import tool
from schemas.output_schemas import Place
from tools.image_utils import build_image_artifact


MOCK_CAFES = [
    Place(
        name="Revolver Espresso",
        category="cafe",
        neighborhood="Seminyak",
        vibe="Grungy-chic espresso bar. Cult local favourite. Hidden laneway entrance. No frills, exceptional coffee.",
        price_range="$",
        rating=4.7,
        review_count=4820,
        instagram_url="https://www.instagram.com/revolverespresso",
        google_maps_url="https://maps.google.com/?q=Revolver+Espresso+Bali",
        image=None,
        opening_hours="7am–9pm daily",
        must_try="Single-origin pour-over with house-made almond milk",
        insider_tip="Arrive before 9am to snag the courtyard seats — locals queue for them.",
    ),
    Place(
        name="Shelter Café",
        category="cafe",
        neighborhood="Canggu",
        vibe="Surf-meets-wellness. Open-air bamboo structure. Cold brew, smoothie bowls, yoga vibes. Great people-watching.",
        price_range="$$",
        rating=4.5,
        review_count=3210,
        instagram_url="https://www.instagram.com/shelter.bali",
        google_maps_url="https://maps.google.com/?q=Shelter+Cafe+Canggu",
        image=None,
        opening_hours="7am–6pm daily",
        must_try="Mushroom latte + acai bowl with dragonfruit",
        insider_tip="Best spot for post-surf brunch. The breezy second floor fills up after 10am.",
    ),
    Place(
        name="Sensorium",
        category="cafe",
        neighborhood="Uluwatu",
        vibe="Minimalist Scandi-Bali fusion. Ceramic pour-overs, locally roasted beans, zero plastic. Peaceful and unhurried.",
        price_range="$$",
        rating=4.8,
        review_count=1840,
        instagram_url="https://www.instagram.com/sensorium.bali",
        google_maps_url="https://maps.google.com/?q=Sensorium+Cafe+Uluwatu",
        image=None,
        opening_hours="8am–5pm (closed Tuesdays)",
        must_try="Turmeric flat white and the coconut-flour banana loaf",
        insider_tip="Closest café to Alila Villas. Small and intimate — only 20 seats.",
    ),
]

MOCK_BEACH_CLUBS = [
    Place(
        name="Single Fin",
        category="beach_club",
        neighborhood="Uluwatu",
        vibe="The most iconic Bali sunset spot. Cliffs. Surf below. Loud. Alive. Unmissable on a Sunday.",
        price_range="$$",
        rating=4.6,
        review_count=11420,
        instagram_url="https://www.instagram.com/singlefinbali",
        google_maps_url="https://maps.google.com/?q=Single+Fin+Uluwatu",
        image=None,
        opening_hours="8am–12am daily",
        must_try="The house Bintang bucket watching surfers at Uluwatu break below",
        insider_tip="Sunday Sessions (4–10pm) is the weekly event. Get there by 3pm for a good spot. Brings international DJs.",
    ),
    Place(
        name="Ulu Cliffhouse",
        category="beach_club",
        neighborhood="Uluwatu",
        vibe="Members-only aesthetic club. Tiered infinity pools. Sophisticated crowd. Some of the best cocktails in Bali.",
        price_range="$$$",
        rating=4.8,
        review_count=3640,
        instagram_url="https://www.instagram.com/ulucliffhouse",
        google_maps_url="https://maps.google.com/?q=Ulu+Cliffhouse+Bali",
        image=None,
        opening_hours="10am–11pm daily (day pass available)",
        must_try="Ulu Signature Spritz and the yellowfin tuna tacos",
        insider_tip="Book the tiered pool cabana 3 days in advance. Day pass is $50 redeemable on food/drinks.",
    ),
    Place(
        name="Sundays Beach Club",
        category="beach_club",
        neighborhood="Uluwatu",
        vibe="Accessible by cable car to a private beach. Snorkeling, paddleboarding, and loungers in calm turquoise water.",
        price_range="$$$",
        rating=4.7,
        review_count=4980,
        instagram_url="https://www.instagram.com/sundaysbeachclub",
        google_maps_url="https://maps.google.com/?q=Sundays+Beach+Club+Bali",
        image=None,
        opening_hours="8am–10pm daily",
        must_try="Fresh coconut with rum on the beach followed by the catch-of-day ceviche",
        insider_tip="Part of Ungasan Resort — non-guests pay a $50 access fee but it is absolutely worth it for the secluded beach.",
    ),
]

MOCK_RESTAURANTS = [
    Place(
        name="Mozaic Restaurant Gastronomique",
        category="restaurant",
        neighborhood="Ubud",
        vibe="Michelin-calibre fine dining in a garden setting. French-Indonesian fusion tasting menus. Best restaurant in Bali by many accounts.",
        price_range="$$$$",
        rating=4.9,
        review_count=2840,
        instagram_url="https://www.instagram.com/mozaicbali",
        google_maps_url="https://maps.google.com/?q=Mozaic+Restaurant+Ubud",
        image=None,
        opening_hours="6pm–10pm (dinner only, Tue–Sun)",
        must_try="7-course tasting menu with wine pairing. Reserve the garden terrace.",
        insider_tip="Book 2–3 weeks in advance for June. Request chef's table in the kitchen garden.",
    ),
    Place(
        name="Warung Babi Guling Ibu Oka",
        category="restaurant",
        neighborhood="Ubud",
        vibe="Legendary hole-in-the-wall. The best suckling pig in Bali. Anthony Bourdain ate here. Always a queue. Always worth it.",
        price_range="$",
        rating=4.6,
        review_count=9840,
        instagram_url="https://www.instagram.com/ibuoka.babiGuling",
        google_maps_url="https://maps.google.com/?q=Warung+Babi+Guling+Ibu+Oka+Ubud",
        image=None,
        opening_hours="9am–4pm (sell out daily, arrive before 11am)",
        must_try="The full platter — crispy skin, satay, rice, and sambal matah",
        insider_tip="They sell out every single day before 3pm. Order the 'special' — extra crispy skin portion.",
    ),
    Place(
        name="Merah Putih",
        category="restaurant",
        neighborhood="Seminyak",
        vibe="Dramatic 12-meter-high bamboo architecture. Modern Indonesian cuisine elevated to art. Beautiful crowd. Great for a special night.",
        price_range="$$$",
        rating=4.7,
        review_count=5210,
        instagram_url="https://www.instagram.com/merahputihbali",
        google_maps_url="https://maps.google.com/?q=Merah+Putih+Seminyak",
        image=None,
        opening_hours="12pm–11pm daily",
        must_try="Slow-braised beef rendang and the signature jackfruit tacos",
        insider_tip="Ask for an upstairs table — you get a full view of the stunning bamboo ceiling.",
    ),
]

MOCK_GYMS = [
    Place(
        name="Dojo Bali",
        category="gym",
        neighborhood="Canggu",
        vibe="The ultimate coworking-meets-wellness hub. World-class gym, pool, café, spa. Digital nomad favourite.",
        price_range="$$",
        rating=4.7,
        review_count=2340,
        instagram_url="https://www.instagram.com/dojobali",
        google_maps_url="https://maps.google.com/?q=Dojo+Bali+Canggu",
        image=None,
        opening_hours="6am–10pm daily",
        must_try="Morning yoga class followed by a green smoothie at the in-house café",
        insider_tip="Day pass is $18. The Sunday morning yoga on the rooftop is the best class in Bali.",
    ),
    Place(
        name="Serenity Eco Guesthouse",
        category="gym",
        neighborhood="Canggu",
        vibe="Boutique wellness retreat with yoga shalas and a serious workout space. Intimate. Community-driven.",
        price_range="$",
        rating=4.5,
        review_count=1120,
        instagram_url="https://www.instagram.com/serenitybali",
        google_maps_url="https://maps.google.com/?q=Serenity+Eco+Canggu",
        image=None,
        opening_hours="6am–8pm daily",
        must_try="Yin yoga at sunset — held in open bamboo shala with rice paddy views",
        insider_tip="Drop-in classes are $12. The teachers are among the most trained instructors in Bali.",
    ),
]

MOCK_NIGHTLIFE = [
    Place(
        name="Mrs Sippy",
        category="nightlife",
        neighborhood="Seminyak",
        vibe="Iconic adults-only swim club that becomes a party after 4pm. Champagne, DJs, beautiful crowd.",
        price_range="$$$",
        rating=4.5,
        review_count=6840,
        instagram_url="https://www.instagram.com/mrssippybali",
        google_maps_url="https://maps.google.com/?q=Mrs+Sippy+Bali",
        image=None,
        opening_hours="11am–12am daily",
        must_try="Aperol spritz by the pool during sunset DJ set",
        insider_tip="Thursday and Saturday nights have the best DJs. Get a pool table — it's a game changer.",
    ),
    Place(
        name="La Favela",
        category="nightlife",
        neighborhood="Seminyak",
        vibe="Hidden bar inside a 1930s Balinese villa. Secret-garden aesthetic. Intimate and theatrical. Great cocktails.",
        price_range="$$$",
        rating=4.6,
        review_count=4210,
        instagram_url="https://www.instagram.com/lafavelabali",
        google_maps_url="https://maps.google.com/?q=La+Favela+Seminyak",
        image=None,
        opening_hours="5pm–3am daily",
        must_try="The 'Hidden Passage' signature cocktail (mezcal, lychee, black salt rim)",
        insider_tip="Arrive between 8–9pm to explore the secret rooms before the crowd arrives after 10pm.",
    ),
]


@tool("search_places")
def search_places(destination: str, categories: str, vibe_keywords: str) -> str:
    """Search for places (cafes, restaurants, beach clubs, gyms, nightlife) matching vibe preferences."""
    time.sleep(0.4)

    all_cafes = [p.model_copy(update={"image": build_image_artifact("cafe_bali")}) for p in MOCK_CAFES]
    all_beach_clubs = [p.model_copy(update={"image": build_image_artifact("beach_club")}) for p in MOCK_BEACH_CLUBS]
    all_restaurants = [p.model_copy(update={"image": build_image_artifact("warung_food")}) for p in MOCK_RESTAURANTS]
    all_gyms = MOCK_GYMS
    all_nightlife = MOCK_NIGHTLIFE

    result = {
        "destination": destination,
        "vibe_match": vibe_keywords,
        "cafes": [p.model_dump() for p in all_cafes],
        "beach_clubs": [p.model_dump() for p in all_beach_clubs],
        "restaurants": [p.model_dump() for p in all_restaurants],
        "gyms": [p.model_dump() for p in all_gyms],
        "nightlife": [p.model_dump() for p in all_nightlife],
        "curation_notes": (
            "Curated to match: aesthetic, wellness, good food, some nightlife. "
            "Avoided large tour group spots. Prioritized locally-loved venues with authentic character."
        ),
        "warnings": [
            "Single Fin Sunday Sessions can feel touristy despite being locally loved — worth experiencing once.",
            "Warung Babi Guling requires early arrival — they sell out before 3pm daily.",
        ],
    }
    return json.dumps(result, indent=2, default=str)


@tool("search_instagram_locations")
def search_instagram_locations(location_tag: str) -> str:
    """Search Instagram location tags to validate a place's aesthetic and popularity."""
    time.sleep(0.25)
    result = {
        "location_tag": location_tag,
        "total_posts": "47.2K",
        "engagement_trend": "rising",
        "top_content_type": "sunset photography, food flatlays, pool shots",
        "aesthetic_score": 9.1,
        "notes": f"#{location_tag.replace(' ', '').lower()} shows strong organic engagement. Not dominated by sponsored content.",
    }
    return json.dumps(result, indent=2)


@tool("search_tiktok_mentions")
def search_tiktok_mentions(place_name: str) -> str:
    """Search TikTok for viral mentions and trending content about a place."""
    time.sleep(0.2)
    result = {
        "place": place_name,
        "total_views": "2.8M",
        "trending_videos": 14,
        "sentiment": "overwhelmingly positive",
        "top_content_themes": ["sunset views", "cocktails", "vibe check", "travel tip"],
        "virality_score": 8.4,
        "notes": f"{place_name} has strong Gen-Z and millennial travel content. Multiple videos >500K views.",
    }
    return json.dumps(result, indent=2)


@tool("get_google_reviews")
def get_google_reviews(place_name: str) -> str:
    """Fetch Google Maps review summary for a place."""
    time.sleep(0.2)
    reviews = {
        "place": place_name,
        "google_rating": 4.6,
        "total_reviews": 3240,
        "review_breakdown": {"5★": "71%", "4★": "18%", "3★": "6%", "2★": "3%", "1★": "2%"},
        "keyword_highlights": ["stunning views", "great cocktails", "sunset magic", "must visit"],
        "recent_low_reviews": ["Slight overcrowding on weekends — go early or on weekdays"],
        "verdict": "Strongly recommended. Reviews are authentic and recent. No suspicious patterns.",
    }
    return json.dumps(reviews, indent=2)
