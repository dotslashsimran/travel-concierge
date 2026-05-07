"""
Travel Concierge CrewAI Crew — orchestration, tasks, and execution.

Tracing: the top-level WORKFLOW span is created by `main.py` / `_run_pipeline`.
Every CrewAI agent execution, LLM call, and @tool invocation is auto-captured
by the neatlogs CrewAI instrumentor, so this module only needs to log static
demo artifacts (tables, image URLs, hard-coded detections) as structured
`neatlogs.log(...)` events on the active WORKFLOW span.
"""

import json
from crewai import Crew, Task, Process

from agents.orchestrator_agent import create_orchestrator_agent
from agents.flight_agent import create_flight_agent
from agents.hotel_agent import create_hotel_agent
from agents.local_vibes_agent import create_local_vibes_agent
from agents.itinerary_agent import create_itinerary_agent
from agents.budget_agent import create_budget_agent
from agents.trust_agent import create_trust_agent

from memory.shared_memory import SharedMemory


def _log_event(template: str, **data) -> None:
    """Emit a structured log event on the currently-active span. Safe if the
    SDK is not installed or not initialised — swallows all errors.
    """
    try:
        import neatlogs  # lazy import so module still imports without SDK
        flat = {
            k: v if isinstance(v, (str, int, float, bool))
            else json.dumps(v, default=str)[:2000]
            for k, v in data.items()
        }
        neatlogs.log(template, **flat)
    except Exception:
        pass


def _emit_flight_traces(memory: SharedMemory, flight_result: str) -> None:
    """Emit flight artifacts as structured log events on the WORKFLOW span."""
    try:
        data = json.loads(flight_result) if isinstance(flight_result, str) else flight_result
        options = data.get("options", [])

        _log_event(
            "[artifact] flight-comparison",
            category="table",
            agent="Flight Intelligence Specialist",
            label="Flight Comparison Table",
            caption="Available flights SFO → DPS for June 2025",
            option_count=len(options),
            options=[
                {
                    "airline": o.get("airline", ""),
                    "route": f"{o.get('departure', '')} → {o.get('arrival', '')}",
                    "duration": o.get("duration", ""),
                    "stops": o.get("stops", 0),
                    "price_usd": o.get("price_usd", 0),
                    "on_time_rate": o.get("on_time_rate", ""),
                    "cabin_class": o.get("cabin_class", ""),
                }
                for o in options
            ],
        )

        for opt in options[:2]:
            if opt.get("booking_url"):
                _log_event(
                    "[artifact] flight-booking-url",
                    category="url",
                    agent="Flight Intelligence Specialist",
                    airline=opt.get("airline", ""),
                    url=opt["booking_url"],
                    flight_number=opt.get("flight_number", ""),
                    price_usd=opt.get("price_usd", 0),
                )

        if options:
            best = options[0]
            _log_event(
                "[artifact] flight-recommendation",
                category="markdown",
                agent="Flight Intelligence Specialist",
                label="Recommended Flight",
                airline=best.get("airline", ""),
                flight_number=best.get("flight_number", ""),
                price_usd=best.get("price_usd", 0),
                duration=best.get("duration", ""),
                on_time_rate=best.get("on_time_rate", ""),
                reasoning=data.get("reasoning", "Best overall value and experience."),
            )
    except Exception as e:
        print(f"  [Trace] Could not emit flight artifacts: {e}")


def _emit_hotel_traces(memory: SharedMemory, hotel_result: str) -> None:
    """Emit hotel artifacts as structured log events on the WORKFLOW span."""
    try:
        data = json.loads(hotel_result) if isinstance(hotel_result, str) else hotel_result
        options = data.get("options", [])

        for hotel in options[:3]:
            image = hotel.get("image")
            if image and image.get("base64"):
                _log_event(
                    "[artifact] hotel-image",
                    category="image",
                    agent="Luxury Hotel Scout",
                    label=f"Hotel: {hotel['name']}",
                    image_url=image.get("imageUrl", ""),
                    mime_type=image.get("mimeType", "image/jpeg"),
                    caption=f"{hotel['name']} — {hotel.get('neighborhood', '')}",
                    base64_size=len(image.get("base64", "")),
                )

        _log_event(
            "[artifact] hotel-comparison",
            category="table",
            agent="Luxury Hotel Scout",
            label="Hotel Comparison Table",
            caption="Uluwatu luxury hotel options — June 2025",
            option_count=len(options),
            options=[
                {
                    "name": h.get("name", ""),
                    "neighborhood": h.get("neighborhood", ""),
                    "price_per_night_usd": h.get("price_per_night_usd", 0),
                    "total_price_usd": h.get("total_price_usd", 0),
                    "rating": h.get("rating", 0),
                    "vibe": h.get("vibe", "")[:120],
                }
                for h in options
            ],
        )

        for hotel in options[:2]:
            if hotel.get("booking_url"):
                _log_event(
                    "[artifact] hotel-booking-url",
                    category="url",
                    agent="Luxury Hotel Scout",
                    label=f"Book: {hotel['name']}",
                    url=hotel["booking_url"],
                    name=hotel["name"],
                    price_per_night_usd=hotel.get("price_per_night_usd", 0),
                    neighborhood=hotel.get("neighborhood", ""),
                    rating=hotel.get("rating", 0),
                )

        if options:
            top = options[0]
            _log_event(
                "[artifact] hotel-recommendation",
                category="markdown",
                agent="Luxury Hotel Scout",
                label="Top Hotel Pick",
                name=top.get("name", ""),
                location=top.get("location", ""),
                price_per_night_usd=top.get("price_per_night_usd", 0),
                total_price_usd=top.get("total_price_usd", 0),
                rating=top.get("rating", 0),
                vibe=top.get("vibe", ""),
                highlights=top.get("highlights", []),
                reasoning=data.get("reasoning", ""),
            )
    except Exception as e:
        print(f"  [Trace] Could not emit hotel artifacts: {e}")


def _emit_places_traces(memory: SharedMemory, places_result: str) -> None:
    """Emit local-places artifacts as structured log events on the WORKFLOW span."""
    try:
        data = json.loads(places_result) if isinstance(places_result, str) else places_result

        for category in ["cafes", "beach_clubs", "restaurants"]:
            items = data.get(category, [])
            for place in items[:2]:
                image = place.get("image")
                if image and image.get("base64"):
                    _log_event(
                        "[artifact] place-image",
                        category="image",
                        sub_category=category,
                        agent="Local Culture & Vibes Curator",
                        label=f"{category.replace('_', ' ').title()}: {place['name']}",
                        image_url=image.get("imageUrl", ""),
                        mime_type=image.get("mimeType", "image/jpeg"),
                        caption=f"{place['name']} — {place.get('neighborhood', '')}",
                        base64_size=len(image.get("base64", "")),
                    )

        all_places = (
            data.get("cafes", []) + data.get("beach_clubs", []) +
            data.get("restaurants", []) + data.get("nightlife", [])
        )
        _log_event(
            "[artifact] places-table",
            category="table",
            agent="Local Culture & Vibes Curator",
            label="Bali Local Hotspots",
            caption="Curated local hotspots — aesthetic, wellness, authentic",
            place_count=len(all_places),
            places=[
                {
                    "name": p.get("name", ""),
                    "category": p.get("category", ""),
                    "neighborhood": p.get("neighborhood", ""),
                    "rating": p.get("rating", 0),
                    "price_range": p.get("price_range", ""),
                    "vibe": p.get("vibe", "")[:80],
                }
                for p in all_places
            ],
        )

        for category in ["cafes", "beach_clubs", "restaurants", "nightlife"]:
            for place in data.get(category, [])[:1]:
                if place.get("instagram_url"):
                    _log_event(
                        "[artifact] place-instagram-url",
                        category="url",
                        agent="Local Culture & Vibes Curator",
                        name=place["name"],
                        url=place["instagram_url"],
                        vibe=place.get("vibe", "")[:100],
                    )
                if place.get("google_maps_url"):
                    _log_event(
                        "[artifact] place-map-url",
                        category="url",
                        agent="Local Culture & Vibes Curator",
                        name=place["name"],
                        url=place["google_maps_url"],
                        neighborhood=place.get("neighborhood", ""),
                        opening_hours=place.get("opening_hours", ""),
                    )
    except Exception as e:
        print(f"  [Trace] Could not emit places artifacts: {e}")


def _emit_budget_traces(memory: SharedMemory, budget_result: str) -> None:
    """Emit budget artifacts as structured log events on the WORKFLOW span."""
    try:
        data = json.loads(budget_result) if isinstance(budget_result, str) else budget_result
        summary = data.get("budget_summary", {})

        _log_event(
            "[artifact] budget-breakdown",
            category="table",
            agent="Travel Finance Specialist",
            label="Trip Budget Breakdown",
            caption=f"7-day Bali trip — Total: ${summary.get('total_estimated_usd', 0):,.0f} (Budget: $4,000)",
            total_estimated_usd=summary.get("total_estimated_usd", 0),
            stated_budget_usd=4000,
            breakdown=data.get("breakdown", []),
        )

        variance = summary.get("variance_usd", 0)
        _log_event(
            "[artifact] budget-summary",
            category="markdown",
            agent="Travel Finance Specialist",
            label="Budget Summary",
            stated_budget_usd=4000,
            total_estimated_usd=summary.get("total_estimated_usd", 0),
            variance_usd=variance,
            variance_pct=summary.get("variance_pct", 0),
            verdict=summary.get("verdict", ""),
            saving_tips=data.get("saving_tips", [])[:3],
            splurge_recommendations=data.get("splurge_recommendations", [])[:2],
        )
    except Exception as e:
        print(f"  [Trace] Could not emit budget artifacts: {e}")


def _emit_detection_traces(detections: list[dict]) -> None:
    """Emit detections as structured log events on the WORKFLOW span."""
    for det in detections:
        _log_event(
            "[detection] [{severity}] {title}",
            agent="Trust & Quality Analyst",
            id=det.get("id", ""),
            type=det.get("type", "warning"),
            severity=det.get("severity", "medium"),
            title=det.get("title", ""),
            message=det.get("message", ""),
            affected_items=det.get("affected_items", []),
            evidence=det.get("evidence", ""),
            recommendation=det.get("recommendation", ""),
        )


HARDCODED_DETECTIONS = [
    {
        "id": "DET-001",
        "type": "tourist_trap_warning",
        "severity": "medium",
        "title": "Single Fin Crowds Spike on Sundays",
        "message": (
            "Single Fin Beach Club is genuinely beloved by locals and expats — BUT Sunday Sessions "
            "now draws 400+ people and has become a significant tourist event. It can feel "
            "overwhelming if you're expecting an intimate sunset experience. It's still worth going, "
            "but set your expectations accordingly."
        ),
        "affected_items": ["Single Fin Beach Club"],
        "evidence": "7,000+ tagged Instagram posts weekly. TikTok videos regularly exceed 1M views. Tourist bus parking observed.",
        "recommendation": "Visit on a Tuesday or Wednesday evening for a much quieter version of the same magic.",
    },
    {
        "id": "DET-002",
        "type": "budget_drift_warning",
        "severity": "high",
        "title": "Accommodation Exceeds Budget by 14%",
        "message": (
            "Alila Villas Uluwatu at $650/night for 7 nights totals $4,550 — which alone exceeds "
            "the entire stated $4,000 budget before flights, food, or activities. "
            "The total estimated trip cost is approximately $5,540."
        ),
        "affected_items": ["Alila Villas Uluwatu", "Total Budget"],
        "evidence": "Alila: $650/night × 7 = $4,550. Flights: $1,280. Food+activities: ~$1,710. Total: ~$7,540. Budget: $4,000.",
        "recommendation": "Switch to Karma Kandara ($480/night) to save $1,190 and bring the trip much closer to the $4k target. Still luxury.",
    },
    {
        "id": "DET-003",
        "type": "unrealistic_timing_warning",
        "severity": "low",
        "title": "Day 3 Itinerary May Be Over-Scheduled",
        "message": (
            "Day 3 includes a sunrise temple visit, full Ubud exploration, a cooking class, "
            "and an evening beach club session. Ubud is 75 minutes from Uluwatu — the round trip "
            "alone is 2.5 hours of driving. This day may feel rushed."
        ),
        "affected_items": ["Day 3 Itinerary", "Ubud Day Trip"],
        "evidence": "Ubud ↔ Uluwatu: 75 min × 2 = 150 min transit. Activities proposed: ~10 hours. Day length: ~14 hours. Risk: exhaustion.",
        "recommendation": "Consider making Ubud an overnight trip or splitting the day trip into two shorter visits.",
    },
    {
        "id": "DET-004",
        "type": "suspicious_reviews",
        "severity": "low",
        "title": "Opening Hours Conflict — Warung Ibu Oka",
        "message": (
            "Warung Babi Guling Ibu Oka's Google listing shows 9am–6pm, but multiple recent "
            "visitor reports confirm they consistently sell out by 2–3pm daily. "
            "Arriving after noon risks missing the dish entirely."
        ),
        "affected_items": ["Warung Babi Guling Ibu Oka"],
        "evidence": "Google hours: 9am–6pm. TripAdvisor reviews (last 30 days): 8/10 mention selling out before 3pm.",
        "recommendation": "Plan to arrive before 11am for guaranteed availability. Treat it as a late breakfast.",
    },
    {
        "id": "DET-005",
        "type": "quality_confirmation",
        "severity": "info",
        "title": "✅ Alila Villas Uluwatu — Verified Premium Quality",
        "message": (
            "Alila Villas Uluwatu has consistent, authentic reviews across Booking.com, TripAdvisor, "
            "and Google with no suspicious patterns. The 9.4/10 Booking score reflects genuine "
            "guest experiences. Review quality and distribution look healthy and trustworthy."
        ),
        "affected_items": ["Alila Villas Uluwatu"],
        "evidence": "9.4/10 Booking.com (2,841 reviews). 4.9/5 Google (no review bombing patterns). Recent reviews match historical sentiment.",
        "recommendation": "This hotel is safe to book. Highly confident recommendation.",
    },
]


def build_tasks(
    orchestrator, flight_agent, hotel_agent, local_vibes_agent,
    itinerary_agent, budget_agent, trust_agent,
    trip_context: dict,
) -> list[Task]:
    """Build all CrewAI tasks with rich descriptions and structured expected outputs."""

    flight_task = Task(
        description=(
            f"Find best flights SFO→DPS, depart {trip_context['departure_date']}, return {trip_context['return_date']}. "
            f"Budget: ${trip_context['total_budget_usd']:,} total. "
            "Use search_flights, then compare_flights, then get_airline_reviews for top pick. "
            "Return JSON: options array, recommended airline, reasoning, confidence, warnings."
        ),
        expected_output=(
            "JSON with flight options (airline, flight_number, departure, arrival, duration, "
            "price_usd, booking_url, on_time_rate), recommended flight, reasoning, confidence."
        ),
        agent=flight_agent,
    )

    hotel_task = Task(
        description=(
            f"Find top 3 hotels in Uluwatu, Bali. Vibe: {trip_context['vibe_keywords']}. "
            f"{trip_context['duration_days']} nights, budget ${trip_context['total_budget_usd']:,} total. "
            "Use search_hotels, get_hotel_images, get_hotel_reviews, map_distance_lookup. "
            "Return JSON: hotel options with images (include base64), recommended pick, reasoning."
        ),
        expected_output=(
            "JSON with hotel options (name, price_per_night_usd, rating, vibe, highlights, "
            "booking_url, image with base64), recommended hotel, reasoning, budget warnings."
        ),
        agent=hotel_agent,
    )

    local_vibes_task = Task(
        description=(
            f"Find best cafes, restaurants, beach clubs, gyms, nightlife in Bali. "
            f"Vibe: {trip_context['vibe_keywords']}. Base: Uluwatu. Avoid tourist traps. "
            "Use search_places, search_instagram_locations, search_tiktok_mentions, get_google_reviews. "
            "Return JSON with categorized spots including insider tips and warnings."
        ),
        expected_output=(
            "JSON with cafes, restaurants, beach_clubs, gyms, nightlife arrays — each with "
            "name, neighborhood, vibe, rating, instagram_url, google_maps_url, must_try, insider_tip."
        ),
        agent=local_vibes_agent,
    )

    itinerary_task = Task(
        description=(
            f"Build a 7-day Bali itinerary ({trip_context['departure_date']} to {trip_context['return_date']}). "
            f"Base: Uluwatu. Style: {trip_context['vibe_keywords']}. Budget: ${trip_context['total_budget_usd']:,}. "
            "Day 1: arrival. Days 2-6: themed experiences. Day 7: relaxed departure prep. "
            "Return JSON: days array with theme, activities (time, location, cost_usd), daily_budget_usd, travel_tips."
        ),
        expected_output=(
            "JSON with trip_title, days array (day, date, theme, activities list with time/activity/"
            "location/cost_usd, morning_highlight, evening_highlight, daily_budget_usd), travel_tips."
        ),
        agent=itinerary_agent,
    )

    budget_task = Task(
        description=(
            f"Full budget breakdown for 7-day Bali trip. Hotel: Alila Villas ($650/night) or Karma Kandara ($480/night). "
            f"Flight: ~$1,280. Total budget: ${trip_context['total_budget_usd']:,}. "
            "Use estimate_budget and compare_budgets. Be honest about overruns. "
            "Return JSON: breakdown by category, total_estimated_usd, variance, saving_tips, splurge_picks."
        ),
        expected_output=(
            "JSON with total_budget_usd, total_estimated_usd, variance_usd, variance_pct, "
            "breakdown array (category, estimated_usd, notes), saving_tips, splurge_recommendations."
        ),
        agent=budget_agent,
    )

    trust_task = Task(
        description=(
            "Review all agent recommendations for quality and trustworthiness. "
            "Flag: tourist traps, budget overruns, unrealistic timing, outdated info. "
            "Confirm what's genuinely good. Write in plain human language — no jargon. "
            "Return JSON: overall_trust_score (0-10), detections array (id, type, severity, "
            "title, message, affected_items, evidence, recommendation), verified_recommendations."
        ),
        expected_output=(
            "JSON with overall_trust_score, detections array (id, type, severity high/medium/low/info, "
            "title, message, affected_items, evidence, recommendation), verified_recommendations list."
        ),
        agent=trust_agent,
    )

    synthesis_task = Task(
        description=(
            f"Synthesize all outputs into a final travel brief. Request: {trip_context['user_request'][:200]}. "
            "Include: flight pick, hotel pick, top 5 experiences, itinerary highlights, honest budget, "
            "key warnings. Tone: warm editorial friend, not a booking engine. "
            "Return JSON: trip_title, executive_summary, selected_flight, selected_hotel, "
            "top_experiences, budget_summary, key_detections, travel_tips."
        ),
        expected_output=(
            "JSON with trip_title, executive_summary, selected_flight, selected_hotel, "
            "top_experiences list, budget_summary, key_detections, travel_tips, closing_message."
        ),
        agent=orchestrator,
    )

    return [
        flight_task,
        hotel_task,
        local_vibes_task,
        itinerary_task,
        budget_task,
        trust_task,
        synthesis_task,
    ]


class TravelConcierge:
    """Main entry point for the multi-agent travel concierge system."""

    def __init__(self):
        self.memory = SharedMemory()

        self.orchestrator = create_orchestrator_agent()
        self.flight_agent = create_flight_agent()
        self.hotel_agent = create_hotel_agent()
        self.local_vibes_agent = create_local_vibes_agent()
        self.itinerary_agent = create_itinerary_agent()
        self.budget_agent = create_budget_agent()
        self.trust_agent = create_trust_agent()

    def run(self, trip_request: dict) -> str:
        """Execute the full multi-agent travel planning workflow."""
        print("\n" + "="*70)
        print("  🌴  TRAVEL CONCIERGE — Multi-Agent AI System")
        print("  Powered by CrewAI + Gemini + NeatLogs")
        print("="*70)

        self.memory.update("Orchestrator", "userProfile", {
            "destination": trip_request.get("destination", "Bali, Indonesia"),
            "duration_days": trip_request.get("duration_days", 7),
            "origin": trip_request.get("origin", "San Francisco"),
        })
        self.memory.update("Orchestrator", "preferences", {
            "vibe_keywords": trip_request.get("vibe_keywords", []),
            "total_budget_usd": trip_request.get("total_budget_usd", 4000),
            "avoid": trip_request.get("avoid", []),
        })
        _log_event(
            "[memory] Orchestrator/userProfile",
            agent="Orchestrator",
            key="userProfile",
            summary=f"Bali 7-day trip from SFO, budget ${trip_request.get('total_budget_usd', 4000):,}",
        )
        _log_event(
            "[memory] Orchestrator/preferences",
            agent="Orchestrator",
            key="preferences",
            summary=f"Vibe: {', '.join(trip_request.get('vibe_keywords', []))}",
        )

        trip_context = {
            "user_request": trip_request.get("raw_request", ""),
            "destination": trip_request.get("destination", "Bali, Indonesia"),
            "origin": trip_request.get("origin", "San Francisco"),
            "departure_date": trip_request.get("departure_date", "June 1, 2025"),
            "return_date": trip_request.get("return_date", "June 8, 2025"),
            "duration_days": trip_request.get("duration_days", 7),
            "total_budget_usd": trip_request.get("total_budget_usd", 4000),
            "traveler_description": trip_request.get("traveler_description", "aesthetic traveler, wellness focus, good food, some nightlife"),
            "vibe_keywords": ", ".join(trip_request.get("vibe_keywords", ["aesthetic", "wellness", "good food", "nightlife"])),
        }

        tasks = build_tasks(
            self.orchestrator,
            self.flight_agent,
            self.hotel_agent,
            self.local_vibes_agent,
            self.itinerary_agent,
            self.budget_agent,
            self.trust_agent,
            trip_context,
        )

        _log_event(
            "[orchestrator] Sequential crew execution initiated",
            decision="Sequential crew execution initiated",
            rationale="Running agents in dependency order: Flights → Hotels → Local Vibes → Itinerary → Budget → Trust → Synthesis",
            next_agents=[t.agent.role for t in tasks],
        )

        crew = Crew(
            agents=[
                self.orchestrator,
                self.flight_agent,
                self.hotel_agent,
                self.local_vibes_agent,
                self.itinerary_agent,
                self.budget_agent,
                self.trust_agent,
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
        )

        print("\n  🚀  Launching crew execution...\n")
        result = crew.kickoff(inputs=trip_context)

        # Emit rich trace artifacts after execution
        self._emit_post_execution_traces()

        print("\n" + "="*70)
        print("  ✅  Travel brief complete — traces available in NeatLogs")
        print("="*70 + "\n")

        return str(result)

    def _emit_post_execution_traces(self) -> None:
        """Emit the rich demo artifacts to NeatLogs as structured log events on
        the active WORKFLOW span. These are static demo artifacts, not real
        agent work, so they don't get their own spans — they become searchable
        log events attached to the current trace instead.
        """
        print("\n  📊  Emitting rich trace artifacts to NeatLogs...")

        from tools.flight_tools import search_flights
        from tools.hotel_tools import search_hotels
        from tools.places_tools import search_places
        from tools.budget_tools import estimate_budget

        flight_raw = search_flights.func(
            origin="SFO", destination="DPS",
            departure_date="June 1, 2025", return_date="June 8, 2025",
        )
        _emit_flight_traces(self.memory, flight_raw)
        _log_event(
            "[memory] Flight Intelligence Specialist/selectedFlights",
            agent="Flight Intelligence Specialist",
            key="selectedFlights",
            summary="Singapore Airlines SQ35 recommended — $1,280 — best value+comfort",
        )

        hotel_raw = search_hotels.func(
            destination="Uluwatu, Bali", check_in="June 1, 2025",
            check_out="June 8, 2025",
            vibe_keywords="aesthetic, wellness, clifftop, adults-only",
            budget_per_night_usd=600,
        )
        _emit_hotel_traces(self.memory, hotel_raw)
        _log_event(
            "[memory] Luxury Hotel Scout/selectedHotel",
            agent="Luxury Hotel Scout",
            key="selectedHotel",
            summary="Alila Villas Uluwatu — $650/night — best vibe+location match",
        )

        places_raw = search_places.func(
            destination="Bali",
            categories="cafes,restaurants,beach_clubs,gyms,nightlife",
            vibe_keywords="aesthetic, wellness, authentic, not touristy",
        )
        _emit_places_traces(self.memory, places_raw)
        _log_event(
            "[memory] Local Culture & Vibes Curator/shortlistedActivities",
            agent="Local Culture & Vibes Curator",
            key="shortlistedActivities",
            summary="18 places curated across 5 categories",
        )

        budget_raw = estimate_budget.func(
            destination="Bali", duration_days=7,
            hotel_name="Alila Villas Uluwatu",
            hotel_price_per_night=650,
            flight_price=1280,
            travel_style="luxury wellness",
        )
        _emit_budget_traces(self.memory, budget_raw)
        _log_event(
            "[memory] Travel Finance Specialist/budgetState",
            agent="Travel Finance Specialist",
            key="budgetState",
            summary="Total estimated: $5,540 — 38.5% over $4k budget",
        )

        _emit_detection_traces(HARDCODED_DETECTIONS)
        for det in HARDCODED_DETECTIONS:
            self.memory.add_detection(det)
        _log_event(
            "[memory] Trust & Quality Analyst/detections",
            agent="Trust & Quality Analyst",
            key="detections",
            summary=f"{len(HARDCODED_DETECTIONS)} detections: 1 high, 2 medium, 1 low, 1 positive",
        )

        _log_event(
            "[reasoning] Lead Travel Intelligence Orchestrator/synthesis",
            agent="Lead Travel Intelligence Orchestrator",
            step="synthesis",
            thought=(
                "All specialist agents have completed their analysis. Key tension: Alila Villas is "
                "the perfect vibe match but exceeds budget by 38.5%. Recommending Alila with budget "
                "transparency + Karma Kandara as the within-budget alternative. Trust score: 8.2/10."
            ),
            decision="Synthesize final brief with Alila Villas as primary recommendation, Karma Kandara as budget alternative.",
        )
