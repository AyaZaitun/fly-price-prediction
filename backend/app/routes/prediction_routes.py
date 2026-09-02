from typing import Callable

from fastapi import HTTPException


def build_prediction_response(payload, predictor: Callable, summary_generator: Callable):
    if payload.source_city == payload.destination_city:
        raise HTTPException(status_code=422, detail="Source and destination cities cannot be the same.")

    try:
        prediction = predictor(payload)
        summary = summary_generator(payload, prediction["predicted_price_inr"])
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
        return {
            **prediction,
            "ai_summary": summary,
            "trip_details": trip_details,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Please check your flight details and try again.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="We couldn't calculate the price right now. Please check your flight details and try again.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="We couldn't calculate the price right now. Please check your flight details and try again.") from exc
