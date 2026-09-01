import json
import os
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "prediction_history.jsonl")


def _resolve_history_paths():
    try:
        import backend.main as main_module
    except Exception:  # pragma: no cover
        return DATA_DIR, HISTORY_FILE

    main_data_dir = getattr(main_module, "DATA_DIR", DATA_DIR)
    main_history_file = getattr(main_module, "HISTORY_FILE", HISTORY_FILE)
    return main_data_dir, main_history_file


def save_prediction_record(request_payload: dict, predicted_price_inr: float, predicted_price_jod: float):
    data_dir, history_file = _resolve_history_paths()
    os.makedirs(data_dir, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": request_payload,
        "response": {
            "predicted_price_inr": predicted_price_inr,
            "predicted_price_jod": predicted_price_jod,
        },
    }
    with open(history_file, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
