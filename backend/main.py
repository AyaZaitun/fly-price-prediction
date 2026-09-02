from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.app.services.chat_service import (
        CHAT_MEMORY,
        CHAT_HISTORY_FILE,
        generate_ai_summary,
        generate_chat_reply,
        get_or_create_conversation,
        save_chat_record,
    )
    from backend.app.core.config import CORS_ORIGINS, DATA_DIR, PREDICTION_HISTORY_FILE
    from backend.app.infrastructure.model_loader import load_model
    from backend.app.routes.chat_routes import build_chat_response
    from backend.app.routes.prediction_routes import build_prediction_response
    from backend.app.models.schemas import ChatRequest, FlightPredictionRequest
    from backend.app.services.prediction_service import predict_flight
except ImportError:  # pragma: no cover
    from app.services.chat_service import (
        CHAT_MEMORY,
        CHAT_HISTORY_FILE,
        generate_ai_summary,
        generate_chat_reply,
        get_or_create_conversation,
        save_chat_record,
    )
    from app.core.config import CORS_ORIGINS, DATA_DIR, PREDICTION_HISTORY_FILE
    from app.infrastructure.model_loader import load_model
    from app.routes.chat_routes import build_chat_response
    from app.routes.prediction_routes import build_prediction_response
    from app.models.schemas import ChatRequest, FlightPredictionRequest
    from app.services.prediction_service import predict_flight
HISTORY_FILE = str(PREDICTION_HISTORY_FILE)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_model()
    yield


app = FastAPI(title="FlyPrice AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return build_prediction_response(payload, predict_flight, generate_ai_summary)


@app.post("/chat")
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(__import__("uuid").uuid4())
    trip_context = request.trip_context or {}
    return build_chat_response(
        request,
        conversation_id,
        trip_context,
        get_or_create_conversation,
        generate_chat_reply,
        save_chat_record,
    )
