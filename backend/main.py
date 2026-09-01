import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from backend.app.chat_service import (
        CHAT_MEMORY,
        CHAT_HISTORY_FILE,
        generate_ai_summary,
        generate_chat_reply,
        get_or_create_conversation,
        save_chat_record,
    )
    from backend.app.model_loader import load_model
    from backend.app.schemas import FlightPredictionRequest
    from backend.app.service import predict_flight
    from backend.app.storage import DATA_DIR, HISTORY_FILE
except ImportError:  # pragma: no cover
    from app.chat_service import (
        CHAT_MEMORY,
        CHAT_HISTORY_FILE,
        generate_ai_summary,
        generate_chat_reply,
        get_or_create_conversation,
        save_chat_record,
    )
    from app.model_loader import load_model
    from app.schemas import FlightPredictionRequest
    from app.service import predict_flight
    from app.storage import DATA_DIR, HISTORY_FILE


def load_project_env() -> None:
    env_candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parent / ".env",
    ]
    for env_path in env_candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = [part.strip() for part in stripped.split("=", 1)]
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


load_project_env()

app = FastAPI(title="FlyPrice AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    load_model()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    trip_context: dict[str, Any] | None = None
    conversation_id: str | None = None


@app.get("/")
def home():
    return {"message": "FlyPrice AI API is running."}


@app.get("/predict")
def predict_get(
    airline: str = Query(...),
    source_city: str = Query(...),
    departure_time: str = Query(...),
    stops: str = Query(...),
    arrival_time: str = Query(...),
    destination_city: str = Query(...),
    class_: str | None = Query(default=None, alias="class"),
    duration: float = Query(...),
    days_left: int = Query(...),
    flight: str | None = Query(default=None),
    month: str | None = Query(default=None),
    holiday: str | None = Query(default=None),
    trip_purpose: str | None = Query(default=None),
):
    payload = FlightPredictionRequest(
        airline=airline,
        flight=flight,
        source_city=source_city,
        departure_time=departure_time,
        stops=stops,
        arrival_time=arrival_time,
        destination_city=destination_city,
        class_=class_,
        duration=duration,
        days_left=days_left,
        month=month,
        holiday=holiday,
        trip_purpose=trip_purpose,
    )
    return _predict_payload(payload)


@app.post("/predict")
def predict(payload: FlightPredictionRequest):
    return _predict_payload(payload)


def _predict_payload(payload: FlightPredictionRequest):
    if payload.source_city == payload.destination_city:
        raise HTTPException(status_code=422, detail="Source and destination cities cannot be the same.")

    try:
        prediction = predict_flight(payload)
        summary = generate_ai_summary(payload, prediction["predicted_price_inr"])
        trip_details = {
            "source_city": payload.source_city,
            "destination_city": payload.destination_city,
            "airline": payload.airline,
            "class": payload.class_ or "",
            "stops": payload.stops,
            "departure_time": payload.departure_time,
            "arrival_time": payload.arrival_time,
            "duration": payload.duration,
            "days_left": payload.days_left,
            "month": payload.month,
            "holiday": payload.holiday,
            "trip_purpose": payload.trip_purpose,
            "flight": payload.flight,
        }
        response = {
            **prediction,
            "ai_summary": summary,
            "trip_details": trip_details,
        }
        return response
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Please check your flight details and try again.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="We couldn't calculate the price right now. Please check your flight details and try again.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="We couldn't calculate the price right now. Please check your flight details and try again.") from exc


@app.post("/chat")
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(__import__("uuid").uuid4())
    trip_context = request.trip_context or {}
    memory = get_or_create_conversation(conversation_id, trip_context)

    response_text = generate_chat_reply(memory, memory["trip_context"], request.message)
    memory["messages"].append({"role": "user", "content": request.message})
    memory["messages"].append({"role": "assistant", "content": response_text})
    save_chat_record(
        conversation_id=conversation_id,
        trip_context=memory["trip_context"],
        user_message=request.message,
        assistant_response=response_text,
    )

    return {
        "conversation_id": conversation_id,
        "assistant_response": response_text,
        "trip_context": memory["trip_context"],
    }
