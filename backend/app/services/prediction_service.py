import pandas as pd

try:
    from backend.app.infrastructure.model_loader import get_model
    from backend.app.repositories.prediction_repository import save_prediction_record
    from backend.app.utils import normalize_holiday, normalize_month, normalize_time, normalize_stop, normalize_trip_purpose
except ImportError:  # pragma: no cover
    from app.infrastructure.model_loader import get_model
    from app.repositories.prediction_repository import save_prediction_record
    from app.utils import normalize_holiday, normalize_month, normalize_time, normalize_stop, normalize_trip_purpose


def build_prediction_record(payload):
    stops_mapping = {"zero": 0, "one": 1, "two_or_more": 2}
    normalized_stops = normalize_stop(payload.stops)
    stops_numeric = stops_mapping.get(normalized_stops, 0)

    return {
        "source_city": payload.source_city,
        "departure_time": normalize_time(payload.departure_time),
        "stops": stops_numeric,
        "arrival_time": normalize_time(payload.arrival_time),
        "destination_city": payload.destination_city,
        "class": payload.class_,
        "duration": float(payload.duration),
        "days_left": int(payload.days_left),
    }


def build_request_log(payload):
    return {
        "airline": payload.airline,
        "flight": payload.flight,
        "source_city": payload.source_city,
        "departure_time": payload.departure_time,
        "stops": payload.stops,
        "arrival_time": payload.arrival_time,
        "destination_city": payload.destination_city,
        "class": payload.class_,
        "duration": payload.duration,
        "days_left": payload.days_left,
        "month": normalize_month(payload.month),
        "holiday": normalize_holiday(payload.holiday),
        "trip_purpose": normalize_trip_purpose(payload.trip_purpose),
    }


def predict_flight(payload):
    model = get_model()
    record = build_prediction_record(payload)
    prediction = float(model.predict(pd.DataFrame([record]))[0])
    predicted_price_inr = max(prediction, 0.0)
    predicted_price_jod = predicted_price_inr * 0.0085

    response = {
        "predicted_price_inr": round(predicted_price_inr, 2),
        "predicted_price_jod": round(predicted_price_jod, 2),
    }
    save_prediction_record(
        request_payload=build_request_log(payload),
        predicted_price_inr=response["predicted_price_inr"],
        predicted_price_jod=response["predicted_price_jod"],
    )
    return response
