import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import backend.app.services.chat_service as chat_service
import backend.main as main
from backend.main import app

client = TestClient(app)


def test_predict_returns_valid_response(monkeypatch):
    monkeypatch.setattr(main, "generate_ai_summary", lambda payload, predicted_price_inr: "AI summary")
    payload = {
        "airline": "Vistara",
        "flight": "UK-123",
        "source_city": "Delhi",
        "departure_time": "Morning",
        "stops": "one",
        "arrival_time": "Afternoon",
        "destination_city": "Mumbai",
        "class": "Economy",
        "duration": 5.5,
        "days_left": 20,
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {"predicted_price_inr", "predicted_price_jod", "ai_summary", "trip_details"}
    assert body["predicted_price_inr"] > 0
    assert body["predicted_price_jod"] > 0
    assert body["ai_summary"] == "AI summary"


def test_predict_rejects_invalid_stops_mapping():
    payload = {
        "airline": "Vistara",
        "flight": "UK-123",
        "source_city": "Delhi",
        "departure_time": "Morning",
        "stops": "1 Stop",
        "arrival_time": "Afternoon",
        "destination_city": "Mumbai",
        "class": "Economy",
        "duration": 5.5,
        "days_left": 20,
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_predict_rejects_same_source_and_destination():
    payload = {
        "airline": "Vistara",
        "flight": "UK-123",
        "source_city": "Delhi",
        "departure_time": "Morning",
        "stops": "zero",
        "arrival_time": "Afternoon",
        "destination_city": "Delhi",
        "class": "Economy",
        "duration": 5.5,
        "days_left": 20,
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_get_predict_accepts_query_params():
    response = client.get(
        "/predict",
        params={
            "airline": "Vistara",
            "flight": "UK-123",
            "source_city": "Delhi",
            "departure_time": "Morning",
            "stops": "one",
            "arrival_time": "Afternoon",
            "destination_city": "Mumbai",
            "class": "Economy",
            "duration": 5.5,
            "days_left": 20,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {"predicted_price_inr", "predicted_price_jod", "ai_summary", "trip_details"}
    assert body["predicted_price_inr"] > 0
    assert body["predicted_price_jod"] > 0
    assert isinstance(body["ai_summary"], str)
    assert body["trip_details"]["destination_city"] == "Mumbai"


def test_predict_saves_prediction_record(tmp_path, monkeypatch):
    temp_file = tmp_path / "prediction_history.jsonl"
    monkeypatch.setattr(main, "HISTORY_FILE", str(temp_file))
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main, "generate_ai_summary", lambda payload, predicted_price_inr: "AI summary")

    payload = {
        "airline": "Vistara",
        "flight": "UK-123",
        "source_city": "Delhi",
        "departure_time": "Morning",
        "stops": "one",
        "arrival_time": "Afternoon",
        "destination_city": "Mumbai",
        "class": "Economy",
        "duration": 5.5,
        "days_left": 20,
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 200, response.text
    assert temp_file.exists()
    content = temp_file.read_text(encoding="utf-8").strip()
    assert content
    record = json.loads(content.splitlines()[-1])
    assert record["request"]["source_city"] == "Delhi"
    assert "predicted_price_inr" in record["response"]
    assert "predicted_price_jod" in record["response"]


def test_chat_returns_assistant_reply(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "CHAT_HISTORY_FILE", str(tmp_path / "chat_history.jsonl"))
    monkeypatch.setattr(main, "CHAT_MEMORY", {})
    monkeypatch.setattr(main, "generate_chat_reply", lambda conversation, trip_context, user_message: "Mumbai has Gateway of India and Colaba.")

    response = client.post(
        "/chat",
        json={
            "message": "What should I visit?",
            "trip_context": {"destination_city": "Mumbai", "source_city": "Delhi", "predicted_price_inr": 12500},
            "conversation_id": "session-1",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["assistant_response"] == "Mumbai has Gateway of India and Colaba."
    assert body["conversation_id"] == "session-1"


def test_chat_resets_memory_when_trip_changes(monkeypatch):
    monkeypatch.setattr(chat_service, "CHAT_MEMORY", {
        "trip-session": {
            "trip_context": {"destination_city": "Chennai", "source_city": "Bangalore", "predicted_price_inr": 5000},
            "messages": [{"role": "assistant", "content": "Chennai has Marina Beach, Fort St. George, and Mylapore."}],
        }
    })

    memory = chat_service.get_or_create_conversation(
        "trip-session",
        {"destination_city": "Delhi", "source_city": "Chennai", "predicted_price_inr": 8000},
    )

    assert memory["trip_context"]["destination_city"] == "Delhi"
    assert memory["messages"] == []


def test_chat_uses_general_fallback_when_llm_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(chat_service, "CHAT_HISTORY_FILE", str(tmp_path / "chat_history.jsonl"))
    monkeypatch.setattr(chat_service, "CHAT_MEMORY", {})
    monkeypatch.setattr(chat_service, "call_llm", lambda prompt: None)

    response = client.post(
        "/chat",
        json={
            "message": "From where you get the price?",
            "trip_context": {"destination_city": "Chennai", "source_city": "Delhi", "airline": "AirIndia", "predicted_price_inr": 12500},
            "conversation_id": "session-price",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "I don’t have reliable current information" in body["assistant_response"]
    assert "Marina Beach" not in body["assistant_response"]


def test_chat_weather_question_uses_generic_fallback_when_llm_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(chat_service, "CHAT_HISTORY_FILE", str(tmp_path / "chat_history.jsonl"))
    monkeypatch.setattr(chat_service, "CHAT_MEMORY", {})
    monkeypatch.setattr(chat_service, "call_llm", lambda prompt: None)

    response = client.post(
        "/chat",
        json={
            "message": "what will be the weather when i arrive",
            "trip_context": {"destination_city": "Chennai", "source_city": "Delhi", "predicted_price_inr": 12500},
            "conversation_id": "session-weather",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "I don’t have reliable current information" in body["assistant_response"]
    assert "Marina Beach" not in body["assistant_response"]


def test_chat_calculates_total_for_multiple_travelers(monkeypatch, tmp_path):
    monkeypatch.setattr(chat_service, "CHAT_HISTORY_FILE", str(tmp_path / "chat_history.jsonl"))
    monkeypatch.setattr(chat_service, "CHAT_MEMORY", {})

    response = client.post(
        "/chat",
        json={
            "message": "if i will travel with 5 persons",
            "trip_context": {
                "destination_city": "Hyderabad",
                "predicted_price_inr": 4503.65,
                "predicted_price_jod": 38.28,
            },
            "conversation_id": "session-group-price",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "₹22,518" in body["assistant_response"]
    assert "191.40 JOD" in body["assistant_response"]
