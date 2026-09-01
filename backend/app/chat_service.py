import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

try:
    from backend.app.schemas import FlightPredictionRequest
    from backend.app.storage import DATA_DIR
except ImportError:  # pragma: no cover
    from app.schemas import FlightPredictionRequest
    from app.storage import DATA_DIR


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"


def get_llm_config() -> tuple[str, str | None]:
    return (
        os.getenv("LLM_MODEL") or DEFAULT_LLM_MODEL,
        os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY"),
    )

CHAT_HISTORY_FILE = os.path.join(DATA_DIR, "chat_history.jsonl")

CHAT_MEMORY: dict[str, dict[str, Any]] = {}


# ============================================================
# FALLBACK PREDICTION SUMMARY
# ============================================================

def fallback_prediction_summary(
    payload: FlightPredictionRequest,
    predicted_price_inr: float,
) -> str:

    destination = payload.destination_city
    airline = payload.airline

    route = f"{payload.source_city} to {destination}"

    return (
        f"Your estimated flight price is ₹{predicted_price_inr:,.0f} "
        f"for a {airline} trip from {route}. "
        f"This is a planning estimate based on your trip details. ✈️"
    )


# ============================================================
# BUILD LLM PROMPT
# ============================================================

def build_llm_prompt(
    summary_type: str,
    payload: FlightPredictionRequest | None,
    predicted_price_inr: float | None,
    user_message: str | None,
    trip_context: dict[str, Any] | None = None,
) -> str:

    facts: list[str] = []

    if payload is not None:

        facts.append(
            f"Destination: {payload.destination_city}"
        )

        facts.append(
            f"Source: {payload.source_city}"
        )

        facts.append(
            f"Airline: {payload.airline}"
        )

        facts.append(
            f"Class: {payload.class_ or 'Not provided'}"
        )

        facts.append(
            f"Stops: {payload.stops}"
        )

        facts.append(
            f"Departure time: {payload.departure_time}"
        )

        facts.append(
            f"Arrival time: {payload.arrival_time}"
        )

        facts.append(
            f"Duration: {payload.duration} hours"
        )

        facts.append(
            f"Days left: {payload.days_left}"
        )

        if payload.month:
            facts.append(
                f"Month: {payload.month}"
            )

        if payload.holiday:
            facts.append(
                f"Holiday: {payload.holiday}"
            )

        if payload.trip_purpose:
            facts.append(
                f"Trip purpose: {payload.trip_purpose}"
            )

    if predicted_price_inr is not None:

        facts.append(
            f"Predicted price: ₹{predicted_price_inr:,.0f}"
        )

    if trip_context:

        for key, value in trip_context.items():

            if value is None or value == "":
                continue

            label = key.replace("_", " ").title()

            facts.append(
                f"{label}: {value}"
            )

    prompt_lines = [
        "TRUSTED APPLICATION DATA",
        *[f"- {fact}" for fact in facts],
    ]

    if summary_type == "prediction":

        prompt_lines += [
            "",
            "USER MESSAGE",
            "Explain the already calculated flight price estimate.",
            "",
            "RULES:",
            "- Use only the trusted application data.",
            "- Do not invent another price.",
            "- Do not change the predicted price.",
            "- Explain that this is an estimate for planning.",
            "- Mention relevant trip factors such as route, airline, stops, timing, or days left.",
            "- Keep the answer under 40 words.",
        ]

    else:

        prompt_lines += [
            "",
            f"QUESTION CATEGORY: {detect_question_intent(user_message or '')}",
            "LATEST USER QUESTION",
            user_message or "",
            "",
            "RULES:",
            "- Answer ONLY the latest question.",
            "- Do not answer a previous question.",
            "- Do not repeat the previous assistant answer.",
            "- Answer the exact topic requested.",
            "- Keep the answer between 1 and 4 short sentences.",
            "- Keep it under 60 words.",
        ]

    return "\n".join(prompt_lines)


# ============================================================
# CALL GROQ
# ============================================================

def call_llm(
    messages: list[dict[str, str]]
) -> str | None:

    llm_model, llm_api_key = get_llm_config()

    if not llm_api_key:
        return None

    try:

        response = httpx.post(

            "https://api.groq.com/openai/v1/chat/completions",

            headers={
                "Authorization": f"Bearer {llm_api_key}",
                "Content-Type": "application/json",
            },

            json={
                "model": llm_model,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 250,
            },

            timeout=25,
        )

        response.raise_for_status()

        data = response.json()

        content = (
            data["choices"][0]["message"]["content"]
            .strip()
        )

        return content or None

    except Exception as error:

        print("LLM ERROR:", error)

        return None


# ============================================================
# GENERATE AI PRICE SUMMARY
# ============================================================

def generate_ai_summary(
    payload: FlightPredictionRequest,
    predicted_price_inr: float,
) -> str:

    prompt = build_llm_prompt(
        summary_type="prediction",
        payload=payload,
        predicted_price_inr=predicted_price_inr,
        user_message=None,
    )

    messages = [

        {
            "role": "system",
            "content": """
You are FlyPrice AI.

Explain the already calculated flight price.

Use only trusted application data.

Never invent or change the price.

The displayed price is an estimate for planning purposes.

Keep the answer short and friendly.
""",
        },

        {
            "role": "user",
            "content": prompt,
        },
    ]

    llm_response = call_llm(messages)

    if llm_response:
        return llm_response.strip()

    return fallback_prediction_summary(
        payload,
        predicted_price_inr,
    )


# ============================================================
# QUESTION INTENT DETECTION
# ============================================================

def detect_question_intent(
    user_message: str,
) -> str:

    message = user_message.lower().strip()

    # --------------------------------------------------------
    # TOTAL TRIP BUDGET
    # --------------------------------------------------------

    budget_keywords = [
        "all trip",
        "daily fee",
        "daily fees",
        "daily cost",
        "daily expense",
        "daily expenses",
        "total trip cost",
        "overall trip cost",
        "whole trip",
        "travel expenses",
        "trip budget",
        "excluding flight",
        "apart from the flight",
    ]

    for keyword in budget_keywords:

        if keyword in message:
            return "trip_budget"

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    price_keywords = [
        "why is this price estimated",
        "why is the price estimated",
        "why is this price",
        "why this price",
        "how is the price calculated",
        "how was the price calculated",
        "price estimated",
        "estimated price",
        "flight price",
        "ticket price",
    ]

    for keyword in price_keywords:

        if keyword in message:
            return "price"

    # --------------------------------------------------------
    # FOOD
    # --------------------------------------------------------

    food_keywords = [
        "what food",
        "what foods",
        "food famous",
        "famous food",
        "famous dish",
        "famous dishes",
        "food should i try",
        "foods should i try",
        "what should i eat",
        "what to eat",
        "local food",
        "local foods",
        "food to try",
        "dish should i try",
        "dishes should i try",
    ]

    for keyword in food_keywords:

        if keyword in message:
            return "food"

    # --------------------------------------------------------
    # HOTELS
    # --------------------------------------------------------

    hotel_keywords = [
        "hotel",
        "5 star",
        "five star",
        "five-star",
        "luxury stay",
        "luxury hotel",
        "where should i stay",
    ]

    for keyword in hotel_keywords:

        if keyword in message:
            return "hotels"

    # --------------------------------------------------------
    # PLACES TO VISIT
    # --------------------------------------------------------

    visit_keywords = [
        "where places",
        "historic site",
        "historic sites",
        "historical site",
        "historical sites",
        "history places",
        "what should i visit",
        "where should i visit",
        "places to visit",
        "place to visit",
        "what places",
        "tourist places",
        "attractions",
        "tourist attractions",
        "what should i see",
        "places should i see",
    ]

    for keyword in visit_keywords:

        if keyword in message:
            return "places"

    # --------------------------------------------------------
    # ACTIVITIES
    # --------------------------------------------------------

    activity_keywords = [
        "what can i do",
        "things to do",
        "thing to do",
        "activities",
        "what activities",
        "what can we do",
        "what should i do there",
    ]

    for keyword in activity_keywords:

        if keyword in message:
            return "activities"

    # --------------------------------------------------------
    # WEATHER
    # --------------------------------------------------------

    weather_keywords = [
        "weather",
        "temperature",
        "hot",
        "cold",
        "rain",
        "forecast",
    ]

    for keyword in weather_keywords:

        if keyword in message:
            return "weather"

    # --------------------------------------------------------
    # PACKING
    # --------------------------------------------------------

    packing_keywords = [
        "what should i pack",
        "what to pack",
        "packing",
        "pack for",
    ]

    for keyword in packing_keywords:

        if keyword in message:
            return "packing"

    transport_keywords = [
        "how to get around",
        "how do i get around",
        "public transport",
        "transportation",
        "transport options",
        "taxi",
        "metro",
        "bus",
        "rent a car",
    ]

    for keyword in transport_keywords:

        if keyword in message:
            return "transport"

    best_time_keywords = [
        "best time to visit",
        "best month to visit",
        "when should i visit",
        "when to visit",
        "best season",
    ]

    for keyword in best_time_keywords:

        if keyword in message:
            return "best_time"

    safety_keywords = [
        "is it safe",
        "safe to travel",
        "travel safety",
        "safety tips",
        "is the city safe",
    ]

    for keyword in safety_keywords:

        if keyword in message:
            return "safety"

    itinerary_keywords = [
        "itinerary",
        "travel plan",
        "trip plan",
        "plan my trip",
        "how many days",
        "day trip",
    ]

    for keyword in itinerary_keywords:

        if keyword in message:
            return "itinerary"

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    return "general"


def extract_traveler_count(user_message: str) -> int | None:
    match = re.search(r"\b(?:for|with|travel(?:ing|ling)? with)\s+(\d+)\s+(?:persons?|people|travellers?|travelers?)\b", user_message.lower())
    if match:
        return int(match.group(1))

    word_counts = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    match = re.search(r"\b(?:for|with|travel(?:ing|ling)? with)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:persons?|people|travellers?|travelers?)\b", user_message.lower())
    return word_counts.get(match.group(1)) if match else None


# ============================================================
# GENERATE DETERMINISTIC TRAVEL RESPONSES
# ============================================================

def generate_travel_response(
    intent: str,
    destination: str,
) -> str:

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    if intent == "price":

        return (
            "The displayed price is an estimate for planning purposes. "
            "It is calculated from your trip details, such as the route, "
            "airline, stops, timing, and days left. ✈️"
        )

    if intent == "trip_budget":
        return (
            f"For a full trip to {destination}, budget separately for your flight, "
            "hotel, meals, local transport, activities, and a small emergency buffer. "
            "The app currently predicts airfare only, so I need your number of nights "
            "and travel style (budget, mid-range, or luxury) to estimate the full trip "
            "cost."
        )

    # --------------------------------------------------------
    # PLACES
    # --------------------------------------------------------

    if intent == "places":

        return (
            f"For {destination}, consider visiting the city's main "
            "landmarks, historic sites, old town areas, and popular "
            "cultural attractions. Ask me about a specific type of place "
            "and I can suggest a focused itinerary."
        )

    # --------------------------------------------------------
    # FOOD
    # --------------------------------------------------------

    if intent == "food":

        return (
            f"In {destination}, try local specialties, traditional dishes, "
            "and regional street food. Look for busy local restaurants or "
            "markets, and ask what the day's signature dish is."
        )

    # --------------------------------------------------------
    # HOTELS
    # --------------------------------------------------------

    if intent == "hotels":
        if destination.lower() == "hyderabad":
            return (
                "In Hyderabad, well-known luxury options include Taj Falaknuma Palace, "
                "ITC Kohenur, Park Hyatt Hyderabad, and Trident Hyderabad. "
                "Check current availability, location, and rates before booking."
            )
        return (
            f"For a five-star stay in {destination}, look for established luxury "
            "brands and compare recent guest reviews, location, amenities, and "
            "current rates before booking."
        )

    # --------------------------------------------------------
    # ACTIVITIES
    # --------------------------------------------------------

    if intent == "activities":

        return (
            f"In {destination}, you can explore local landmarks, walk through "
            "historic areas, visit markets, try local food, and experience "
            "the city's culture."
        )

    # --------------------------------------------------------
    # WEATHER
    # --------------------------------------------------------

    if intent == "weather":

        return (
            "I don’t have reliable current information about that."
        )

    # --------------------------------------------------------
    # PACKING
    # --------------------------------------------------------

    if intent == "packing":

        return (
            f"For {destination}, pack comfortable clothes suitable for the "
            "season, comfortable walking shoes, and any personal essentials "
            "you may need during the trip."
        )

    if intent == "transport":
        return (
            f"For getting around {destination}, compare metro or bus routes, "
            "app-based taxis, and hotel-arranged transfers. Choose the option "
            "based on your neighborhood, timing, and luggage."
        )

    if intent == "best_time":
        return (
            f"The best time to visit {destination} depends on weather, crowds, "
            "and your activities. Check the seasonal forecast and local events "
            "for your travel month before booking."
        )

    if intent == "safety":
        return (
            f"For a safer trip to {destination}, use licensed transport, keep "
            "valuables secure, stay in well-lit areas at night, and follow "
            "current local travel advice."
        )

    if intent == "itinerary":
        return (
            f"A good {destination} itinerary can combine major sights, one "
            "historic or cultural area, local food, and time to explore at a "
            "relaxed pace. Tell me how many days you have for a focused plan."
        )

    return ""


def is_flight_only_budget_answer(response: str) -> bool:
    text = response.lower()
    has_flight_only_language = "flight" in text and (
        "estimated cost" in text
        or "estimated price" in text
        or "ticket price" in text
    )
    has_trip_categories = any(
        category in text
        for category in ("hotel", "accommodation", "meals", "transport", "activities")
    )
    return has_flight_only_language and not has_trip_categories


def is_incomplete_answer(response: str) -> bool:
    text = response.strip().rstrip(".!?")
    if not text:
        return True
    return text.split()[-1].lower() in {"i", "we", "because", "and", "or", "the", "a", "an", "to", "for"}


# ============================================================
# GENERATE CHAT REPLY
# ============================================================

def generate_chat_reply(
    conversation: dict[str, Any],
    trip_context: dict[str, Any] | None,
    user_message: str,
) -> str:

    trip_context_data = (
        trip_context
        or conversation.get("trip_context")
        or {}
    )

    # ========================================================
    # FIRST: DETECT INTENT
    # ========================================================

    intent = detect_question_intent(
        user_message
    )

    print(
        f"CHAT MESSAGE: {user_message}"
    )

    print(
        f"DETECTED INTENT: {intent}"
    )

    traveler_count = extract_traveler_count(user_message)
    if traveler_count and intent != "trip_budget":
        price_inr = trip_context_data.get("predicted_price_inr")
        price_jod = trip_context_data.get("predicted_price_jod")
        if price_inr is not None:
            total_inr = float(price_inr) * traveler_count
            response = (
                f"For {traveler_count} travelers, the estimated total is "
                f"₹{total_inr:,.0f} (about ₹{float(price_inr):,.0f} per traveler). "
                "This estimate assumes each traveler has the same flight details "
                "and does not include extra baggage or booking fees."
            )
            if price_jod is not None:
                response += f" That is approximately {float(price_jod) * traveler_count:,.2f} JOD total."
            return response

    # ========================================================
    # GET DESTINATION
    # ========================================================

    destination = (
        trip_context_data.get(
            "destination_city"
        )
        or "your destination"
    )

    # Ask the AI for every normal question so it can use the full trip context.
    # Deterministic topic responses below are used only when the AI is unavailable.

    system_prompt = """
You are FlyPrice AI, a friendly travel assistant.

Answer ONLY the latest user question.

The user may ask different questions during the same conversation.

Do not assume that the latest question is the same as the previous one.

For example:

"What should I visit there?"
→ Recommend places and attractions.

"What food should I try?"
→ Recommend local foods.

"What can I do there?"
→ Recommend activities.

"Why is this price estimated?"
→ Explain the flight price estimate.

Always answer the exact question being asked.

Do not copy previous assistant answers.

You may use general knowledge for:

- attractions
- places to visit
- food
- activities
- culture
- packing
- general travel advice

Use application data only for the user's specific trip.

Never invent:

- current ticket prices
- flight availability
- flight schedules
- hotel availability
- current weather
- visa requirements
- current travel restrictions
- current events

For a total-trip-budget question, do not answer with airfare alone. The application
prediction is only the flight estimate. Explain that a whole-trip estimate also
needs accommodation nights and travel style, then discuss hotel, meals, local
transport, activities, and a contingency budget. Do not confuse days left before
booking with the number of days at the destination.

If the question requires current information that you cannot verify, say:

"I don't have reliable current information about that."

Keep answers friendly, natural, and concise.

Normally use 1-4 short sentences and fewer than 60 words.
"""

    messages: list[dict[str, str]] = [

        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    # ========================================================
    # ADD TRUSTED TRIP CONTEXT
    # ========================================================

    if trip_context_data:

        context_text = "\n".join(

            f"{key.replace('_', ' ').title()}: {value}"

            for key, value in trip_context_data.items()

            if value is not None
            and value != ""
        )

        messages.append(

            {
                "role": "system",

                "content": f"""
TRUSTED TRIP CONTEXT

{context_text}

These values come directly from the application.
Treat them as trusted information.
Do not modify them.
""",
            }
        )

    # ========================================================
    # ADD LIMITED CONVERSATION HISTORY
    # ========================================================

    previous_messages = conversation.get(
        "messages",
        []
    )

    for message in previous_messages[-6:]:

        messages.append(
            {
                "role": message["role"],
                "content": message["content"],
            }
        )

    # ========================================================
    # ADD LATEST QUESTION
    # ========================================================

    messages.append(

        {
            "role": "user",

            "content": f"""
LATEST USER QUESTION:

{user_message}

Answer this question specifically.
Do not answer a previous question.
""",
        }
    )

    # ========================================================
    # CALL LLM
    # ========================================================

    response = call_llm(
        messages
    )

    if response:

        if intent == "trip_budget" and (
            is_flight_only_budget_answer(response)
            or is_incomplete_answer(response)
        ):
            return generate_travel_response(intent, destination)

        return response.strip()

    direct_response = generate_travel_response(
        intent,
        destination,
    )

    if direct_response:
        return direct_response

    return (
        "I don’t have reliable current information about that."
    )


# ============================================================
# SAVE CHAT RECORD
# ============================================================

def save_chat_record(
    conversation_id: str,
    trip_context: dict[str, Any] | None,
    user_message: str,
    assistant_response: str,
):

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    record = {

        "timestamp":
            datetime.now(timezone.utc).isoformat(),

        "conversation_id":
            conversation_id,

        "destination_city":
            (trip_context or {}).get(
                "destination_city"
            ),

        "predicted_price_inr":
            (trip_context or {}).get(
                "predicted_price_inr"
            ),

        "user_message":
            user_message,

        "assistant_response":
            assistant_response,

        "trip_context":
            trip_context or {},
    }

    with open(
        CHAT_HISTORY_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(
                record,
                ensure_ascii=False
            )
            + "\n"
        )


# ============================================================
# GET OR CREATE CONVERSATION
# ============================================================

def get_or_create_conversation(
    conversation_id: str | None,
    trip_context: dict[str, Any] | None,
) -> dict[str, Any]:

    if conversation_id is None:

        conversation_id = str(
            uuid.uuid4()
        )

    conversation = CHAT_MEMORY.setdefault(

        conversation_id,

        {
            "trip_context": {},
            "messages": [],
        }
    )

    if trip_context:

        new_trip_context = {

            key: value

            for key, value in trip_context.items()

            if value not in (None, "")
        }

        existing_trip_context = {

            key: value

            for key, value
            in conversation.get(
                "trip_context",
                {}
            ).items()

            if value not in (None, "")
        }

        same_trip = (

            new_trip_context.get(
                "destination_city"
            )
            ==
            existing_trip_context.get(
                "destination_city"
            )

            and

            new_trip_context.get(
                "source_city"
            )
            ==
            existing_trip_context.get(
                "source_city"
            )

            and

            new_trip_context.get(
                "airline"
            )
            ==
            existing_trip_context.get(
                "airline"
            )
        )

        if (
            not same_trip
            and existing_trip_context
        ):

            conversation[
                "trip_context"
            ] = {}

            conversation[
                "messages"
            ] = []

        conversation[
            "trip_context"
        ].update(
            new_trip_context
        )

    return conversation


# ============================================================
# APPEND CONVERSATION TURN
# ============================================================

def append_conversation_turn(
    conversation: dict[str, Any],
    user_message: str,
    assistant_response: str,
) -> None:

    conversation["messages"].append(

        {
            "role": "user",
            "content": user_message,
        }
    )

    conversation["messages"].append(

        {
            "role": "assistant",
            "content": assistant_response,
        }
    )
