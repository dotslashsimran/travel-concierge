from pydantic import BaseModel, Field
from typing import Any, Optional


class ImageArtifact(BaseModel):
    imageUrl: str
    base64: str
    mimeType: str
    source: str
    caption: str


class FlightOption(BaseModel):
    airline: str
    flight_number: str
    departure: str
    arrival: str
    duration: str
    stops: int
    price_usd: float
    cabin_class: str
    booking_url: str
    airline_logo_url: str
    on_time_rate: str
    luggage_included: bool
    notes: str


class FlightSearchOutput(BaseModel):
    origin: str
    destination: str
    travel_dates: str
    options: list[FlightOption]
    recommended: str
    reasoning: str
    confidence: float
    warnings: list[str]


class HotelOption(BaseModel):
    name: str
    location: str
    neighborhood: str
    price_per_night_usd: float
    total_price_usd: float
    rating: float
    review_count: int
    vibe: str
    highlights: list[str]
    booking_url: str
    map_url: str
    image: Optional[ImageArtifact] = None
    distance_to_beach: str
    distance_to_airport: str


class HotelSearchOutput(BaseModel):
    destination: str
    check_in: str
    check_out: str
    options: list[HotelOption]
    recommended: str
    reasoning: str
    confidence: float
    warnings: list[str]


class Place(BaseModel):
    name: str
    category: str
    neighborhood: str
    vibe: str
    price_range: str
    rating: float
    review_count: int
    instagram_url: str
    google_maps_url: str
    image: Optional[ImageArtifact] = None
    opening_hours: str
    must_try: str
    insider_tip: str


class LocalVibesOutput(BaseModel):
    cafes: list[Place]
    restaurants: list[Place]
    beach_clubs: list[Place]
    gyms: list[Place]
    nightlife: list[Place]
    reasoning: str
    confidence: float
    warnings: list[str]


class DayActivity(BaseModel):
    time: str
    activity: str
    location: str
    category: str
    duration: str
    cost_usd: float
    notes: str
    map_url: str


class DayPlan(BaseModel):
    day: int
    date: str
    theme: str
    neighborhood: str
    activities: list[DayActivity]
    morning_highlight: str
    evening_highlight: str
    daily_budget_usd: float


class ItineraryOutput(BaseModel):
    trip_title: str
    destination: str
    duration_days: int
    travel_style: str
    days: list[DayPlan]
    overview: str
    travel_tips: list[str]
    reasoning: str
    confidence: float


class BudgetCategory(BaseModel):
    category: str
    estimated_usd: float
    breakdown: list[dict[str, Any]]
    notes: str


class BudgetOutput(BaseModel):
    total_budget_usd: float
    total_estimated_usd: float
    variance_usd: float
    variance_pct: float
    categories: list[BudgetCategory]
    budget_verdict: str
    saving_tips: list[str]
    splurge_recommendations: list[str]
    reasoning: str
    confidence: float
    warnings: list[str]


class Detection(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    message: str
    affected_items: list[str]
    evidence: str
    recommendation: str
    agent_source: str


class TrustAnalysisOutput(BaseModel):
    overall_trust_score: float
    detections: list[Detection]
    verified_recommendations: list[str]
    flagged_recommendations: list[str]
    analysis_summary: str
    reasoning: str
    confidence: float


class FinalTravelBrief(BaseModel):
    trip_title: str
    destination: str
    traveler_profile: str
    executive_summary: str
    selected_flight: FlightOption
    selected_hotel: HotelOption
    top_experiences: list[Place]
    itinerary: ItineraryOutput
    budget: BudgetOutput
    trust_score: float
    detections: list[Detection]
    travel_tips: list[str]
    confidence: float
    reasoning_notes: list[str]
