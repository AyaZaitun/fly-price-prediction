import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

try:
    from backend.app.core.config import CHAT_HISTORY_FILE, DEFAULT_LLM_MODEL, LLM_TIMEOUT_SECONDS, LLM_URL
    from backend.app.models.schemas import FlightPredictionRequest
    from backend.app.repositories.chat_repository import save_chat_record
except ImportError:  # pragma: no cover
    from app.core.config import CHAT_HISTORY_FILE, DEFAULT_LLM_MODEL, LLM_TIMEOUT_SECONDS, LLM_URL
    from app.models.schemas import FlightPredictionRequest
    from app.repositories.chat_repository import save_chat_record

MODEL_ALIASES = {
    "gpt-4o-mini": "openai/gpt-oss-120b",
    "llama-3.1-8b-instant": "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
}
CHAT_MEMORY: dict[str, dict[str, Any]] = {}


def get_llm_config() -> tuple[str, str | None]:
    configured_model = os.getenv("LLM_MODEL") or DEFAULT_LLM_MODEL
    return MODEL_ALIASES.get(configured_model, configured_model), os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")


def call_llm(messages: list[dict[str, str]]) -> str | None:
    model, api_key = get_llm_config()
    try:
        request = httpx.post(
            LLM_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.4, "max_tokens": 300},
            timeout=LLM_TIMEOUT_SECONDS,
        ) if api_key else None
        request.raise_for_status()
        return request.json()["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as error:
        print(f"LLM ERROR: {error.response.text}")
        return None
    except Exception as error:
        print(f"LLM ERROR: {error}")
        return None


def _trip_data(payload: FlightPredictionRequest | None = None, predicted_price_inr: float | None = None, trip_context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload_data = payload.model_dump(by_alias=True) if payload else {}
    input_data = {**payload_data, **(trip_context or {})}
    model_output = {
        "predicted_price_inr": predicted_price_inr,
        "predicted_price_jod": (trip_context or {}).get("predicted_price_jod"),
    }
    return {"flight_inputs": input_data, "flight_model_output": model_output}


def build_llm_prompt(summary_type: str, payload: FlightPredictionRequest | None, predicted_price_inr: float | None, user_message: str | None, trip_context: dict[str, Any] | None = None) -> str:
    data = json.dumps(_trip_data(payload, predicted_price_inr, trip_context), ensure_ascii=True, default=str)
    request = user_message or "Explain the flight prediction clearly."
    return f"Purpose: {summary_type}\nComplete flight inputs and model output: {data}\nUser request: {request}"


def generate_ai_summary(payload: FlightPredictionRequest, predicted_price_inr: float) -> str:
    prompt = build_llm_prompt("flight price summary", payload, predicted_price_inr, None)
    response = call_llm([
        {"role": "system", "content": "You are FlyPrice AI. Use the complete flight_inputs object and the flight_model_output object to create a clear, friendly planning summary. Connect the supplied route, timing, airline, stops, class, duration, days left, month, holiday, and purpose to the calculated result. Preserve the model output exactly and keep the summary under 45 words."},
        {"role": "user", "content": prompt},
    ])
    fallback = f"The estimated flight price from {payload.source_city} to {payload.destination_city} is ₹{predicted_price_inr:,.0f}. This is a planning estimate based on the supplied trip details."
    return response or fallback


def generate_chat_reply(conversation: dict[str, Any], trip_context: dict[str, Any] | None, user_message: str) -> str:
    context = trip_context or conversation.get("trip_context") or {}
    traveler_match = re.search(r"\b(?:with|for)\s+(\d+)\s+(?:persons?|people|travelers?|travellers?)\b", user_message.lower())
    traveler_count = int(traveler_match.group(1)) if traveler_match else None
    price_inr = context.get("predicted_price_inr")
    price_jod = context.get("predicted_price_jod")
    if traveler_count and price_inr is not None:
        total_inr = float(price_inr) * traveler_count
        total_jod = float(price_jod) * traveler_count if price_jod is not None else None
        return f"For {traveler_count} travelers, the estimated total is ₹{total_inr:,.0f} (about ₹{float(price_inr):,.0f} per traveler)." + (f" That is approximately {total_jod:,.2f} JOD total." if total_jod is not None else "")
    history = conversation.get("messages", [])[-8:]
    context_data = json.dumps({"flight_inputs": context, "flight_model_output": {"predicted_price_inr": price_inr, "predicted_price_jod": price_jod}}, ensure_ascii=True, default=str)
    messages = [
        {"role": "system", "content": "You are FlyPrice AI, a concise and thoughtful travel assistant. Read both flight_inputs and flight_model_output before answering. Use the user's supplied details and calculated result naturally whenever they help answer the question. Treat application values as factual and use general travel knowledge when helpful. Keep current information qualified and never manufacture live prices, schedules, availability, weather, or official requirements. Respond naturally in 1 to 4 short sentences."},
        {"role": "system", "content": f"Flight inputs and flight model output (JSON): {context_data}"},
        *history,
        {"role": "user", "content": user_message},
    ]
    return call_llm(messages) or "I don’t have reliable current information about that."


def get_or_create_conversation(conversation_id: str | None, trip_context: dict[str, Any] | None) -> dict[str, Any]:
    conversation = CHAT_MEMORY.setdefault(conversation_id or str(uuid.uuid4()), {"trip_context": {}, "messages": []})
    previous = conversation["trip_context"]
    current = trip_context or {}
    same_trip = previous.get("source_city") == current.get("source_city") and previous.get("destination_city") == current.get("destination_city") and previous.get("airline") == current.get("airline")
    if previous and current and not same_trip:
        conversation["trip_context"] = {}
        conversation["messages"] = []
    conversation["trip_context"].update(current)
    return conversation


__all__ = ["CHAT_HISTORY_FILE", "CHAT_MEMORY", "build_llm_prompt", "call_llm", "generate_ai_summary", "generate_chat_reply", "get_llm_config", "get_or_create_conversation", "save_chat_record"]
