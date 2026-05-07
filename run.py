"""
Travel Concierge — 3-Agent Demo
NeatLogs auto-instruments CrewAI + google.genai.
neatlogs.init() must come before any crewai / google.genai imports.
"""

import os, json, time, base64, httpx
from dotenv import load_dotenv
load_dotenv()

# ── init FIRST — before crewai / google.genai ─────────────────────────────────
import neatlogs

tracker = neatlogs.init(
    api_key=os.environ["NEATLOGS_API_KEY"],
    endpoint=os.environ["NEATLOGS_ENDPOINT"],
    workflow_name="travel-concierge",
    instrumentations=["google-genai", "crewai"],
    tags=["travel-concierge", "bali-demo", "investor-demo"],
)

# ── NOW import crewai + google.genai (auto-instrumented from here) ────────────
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
import google.genai as genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

# ── Helpers ───────────────────────────────────────────────────────────────────
def emit_span(name, node_type, provider, messages, completion):
    s = tracker.start_llm_span(model=name, provider=provider,
                                framework="crewai", node_type=node_type, node_name=name)
    s.messages = messages
    s.completion = completion if isinstance(completion, str) else json.dumps(completion, default=str)
    tracker.end_llm_span(s)
    print(f"  ◉  {node_type:16s} {name[:50]}")

def fetch_b64(url):
    try:
        r = httpx.get(url, timeout=8, follow_redirects=True)
        return base64.b64encode(r.content).decode()
    except:
        return ""

# ── Tools ─────────────────────────────────────────────────────────────────────
@tool("search_flights")
def search_flights(origin: str, destination: str) -> str:
    """Search available flights between two cities."""
    time.sleep(0.2)
    return json.dumps([
        {"airline":"Singapore Airlines","flight":"SQ35+SQ947","route":"SFO→SIN→DPS","duration":"19h 35m","price_usd":1280,"on_time_pct":"91%","url":"https://www.singaporeair.com"},
        {"airline":"Cathay Pacific","flight":"CX879+CX711","route":"SFO→HKG→DPS","duration":"21h 35m","price_usd":1095,"on_time_pct":"87%","url":"https://www.cathaypacific.com"},
        {"airline":"Japan Airlines","flight":"JL001+JL725","route":"SFO→NRT→DPS","duration":"23h 15m","price_usd":1410,"on_time_pct":"94%","url":"https://www.jal.com"},
    ])

@tool("compare_flights")
def compare_flights(flight_data: str) -> str:
    """Compare flight options and return the best pick with reasoning."""
    time.sleep(0.15)
    return json.dumps({"winner":"Singapore Airlines SQ35+SQ947","reasoning":"Best price/duration. 91% on-time, 19h 35m, $1,280 — leaves strong budget room for a $4k trip.","savings_vs_jal":130})

@tool("search_hotels")
def search_hotels(destination: str, vibe: str) -> str:
    """Search for hotels matching a destination and vibe."""
    time.sleep(0.25)
    b64_alila = fetch_b64("https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600")
    b64_karma = fetch_b64("https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600")
    return json.dumps([
        {"name":"Alila Villas Uluwatu","price_night":650,"total_7n":4550,"rating":4.9,"vibe":"Clifftop luxury, infinity pools over Indian Ocean, adults-only","url":"https://www.alilahotels.com/uluwatu","image":{"url":"https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600","base64":b64_alila,"caption":"Alila Villas — infinity pool at sunset"}},
        {"name":"Karma Kandara","price_night":480,"total_7n":3360,"rating":4.8,"vibe":"Bohemian clifftop, private beach by cable car, Balinese art","url":"https://www.karma-group.com/karma-kandara","image":{"url":"https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600","base64":b64_karma,"caption":"Karma Kandara — clifftop villa pool"}},
    ])

@tool("check_budget")
def check_budget(hotel_price_night: float, flight_price: float, nights: int) -> str:
    """Calculate full trip cost and check against stated budget."""
    time.sleep(0.1)
    accommodation = hotel_price_night * nights
    total = accommodation + flight_price + 595 + 420 + 280 + 415
    return json.dumps({"accommodation":accommodation,"flights":flight_price,"food_7d":595,"activities":420,"transport":280,"misc":415,"total_estimated":total,"stated_budget":4000,"over_by":round(total-4000,0),"verdict":"Over budget" if total>4000 else "Within budget"})

@tool("audit_recommendations")
def audit_recommendations(places: str) -> str:
    """Audit recommendations for tourist traps or quality issues."""
    time.sleep(0.1)
    return json.dumps({
        "Single Fin Beach Club":{"tourist_index":7.2,"verdict":"Iconic but crowded on Sundays — go midweek"},
        "Alila Villas Uluwatu":{"review_authenticity":"verified","verdict":"Authentic reviews, safe to book"},
        "Kecak Fire Dance":{"tourist_index":9.4,"verdict":"Skip — very touristy, over-commercialised"},
    })

# ── Agents ────────────────────────────────────────────────────────────────────
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

# ── Tasks ─────────────────────────────────────────────────────────────────────
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

# ── Crew kickoff (auto-instrumented: workflow + agent spans) ──────────────────
crew = Crew(
    agents=[flight_agent, hotel_agent, trust_agent],
    tasks=[flight_task, hotel_task, trust_task],
    process=Process.sequential,
    verbose=True,
)

print("\n" + "="*60)
print("  🌴  TRAVEL CONCIERGE — 3-Agent Demo")
print("  CrewAI + Gemini 2.5 Flash + NeatLogs")
print(f"  Endpoint: https://staging-cloud.neatlogs.com")
print("="*60 + "\n")

result = crew.kickoff(inputs={"destination": "Bali", "budget": 4000, "origin": "San Francisco"})

# ── Extra artifact spans ───────────────────────────────────────────────────────
print("\n  Emitting artifact spans...")

emit_span("Flight Comparison Table", "artifact", "Flight Intelligence Specialist",
    [{"role":"user","content":"Flight options SFO→DPS June 2025"}],
    "| Airline | Route | Duration | Price | On-Time |\n|---|---|---|---|---|\n| Singapore Airlines | SFO→SIN→DPS | 19h 35m | $1,280 | 91% |\n| Cathay Pacific | SFO→HKG→DPS | 21h 35m | $1,095 | 87% |\n| Japan Airlines | SFO→NRT→DPS | 23h 15m | $1,410 | 94% |")

for label, url, caption in [
    ("Alila Villas Uluwatu", "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600", "Alila Villas — infinity pool over the Indian Ocean"),
    ("Karma Kandara", "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600", "Karma Kandara — clifftop villa, Bali"),
    ("Uluwatu Cliffs", "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=600", "Uluwatu coastline at golden hour"),
]:
    b64 = fetch_b64(url)
    emit_span(f"Image: {label}", "artifact", "Luxury Hotel Scout",
        [{"role":"user","content":caption}],
        json.dumps({"imageUrl":url,"base64":b64,"mimeType":"image/jpeg","caption":caption}))
    print(f"  🖼  {caption}")

emit_span("Hotel Comparison Table", "artifact", "Luxury Hotel Scout",
    [{"role":"user","content":"Uluwatu hotel options — June 2025"}],
    "| Hotel | $/night | 7-night total | Rating | Vibe |\n|---|---|---|---|---|\n| Alila Villas Uluwatu | $650 | $4,550 | ⭐ 4.9 | Clifftop luxury, adults-only |\n| Karma Kandara | $480 | $3,360 | ⭐ 4.8 | Bohemian, private beach by cable car |")

emit_span("Budget Breakdown", "artifact", "Luxury Hotel Scout",
    [{"role":"user","content":"Full trip budget estimate"}],
    "| Category | Cost |\n|---|---|\n| Flights (SQ) | $1,280 |\n| Hotel Alila 7N | $4,550 |\n| Food & Dining | $595 |\n| Activities | $420 |\n| Transport | $280 |\n| Misc | $415 |\n| **Total** | **$7,540** |\n| Your Budget | $4,000 |\n| Over by | **$3,540** |\n\n⚠️ Switch to Karma Kandara ($480/night) to save $1,190.")

for det_id, severity, title, message, evidence, rec in [
    ("DET-001","high","Hotel Alone Blows the Entire Budget",
     "Alila Villas at $650/night × 7 = $4,550 — more than your whole $4,000 budget before flights or food. Total trip is ~$7,500.",
     "Accommodation: $4,550. Flight: $1,280. Food+activities: ~$1,710. Total: $7,540 vs $4,000 budget.",
     "Switch to Karma Kandara ($480/night) — saves $1,190, still clifftop luxury with a private beach."),
    ("DET-002","medium","Single Fin Sundays Is Now a Tourist Event",
     "Sunday Sessions now draws 400+ people and tourist buses. Worth going — but it's no longer intimate.",
     "7,000+ Instagram tags/week. TikTok: 2.8M views. Tour operators run scheduled shuttles.",
     "Go Tuesday or Wednesday — same cliffs and cocktails, fraction of the crowd."),
    ("DET-003","info","✅ Alila Villas Reviews Are Verified Authentic",
     "Alila has 9.4/10 from 2,841 reviews with no fake patterns. Consistent and genuine. Safe to book.",
     "Healthy distribution. 82% of reviews within 12 months. No rating spikes or bot clusters.",
     "No action needed — book with confidence."),
]:
    emit_span(f"Detection: {title}", "detection", "Trust & Quality Analyst",
        [{"role":"user","content":f"[{severity.upper()}] {title}"}],
        json.dumps({"id":det_id,"severity":severity,"title":title,"message":message,"evidence":evidence,"recommendation":rec}))
    icon = {"high":"🔴","medium":"🟡","info":"🟢"}.get(severity,"⚪")
    print(f"  {icon}  [{severity.upper()}] {title}")

# ── Wait for background threads ────────────────────────────────────────────────
print("\n  Flushing spans...")
if tracker:
    for t in tracker._threads:
        t.join(timeout=8)

print("\n" + "="*60)
print("  ✅  Done — check https://staging-cloud.neatlogs.com")
print("="*60)
