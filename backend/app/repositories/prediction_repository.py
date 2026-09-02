import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from backend.app.core.config import DATA_DIR, PREDICTION_HISTORY_FILE
except ImportError:  # pragma: no cover
    from app.core.config import DATA_DIR, PREDICTION_HISTORY_FILE


def _resolve_paths() -> tuple[Path, Path]:
    try:
        import backend.main as main_module
    except Exception:  # pragma: no cover
        return Path(DATA_DIR), Path(PREDICTION_HISTORY_FILE)
    return Path(getattr(main_module, "DATA_DIR", DATA_DIR)), Path(getattr(main_module, "HISTORY_FILE", PREDICTION_HISTORY_FILE))


def save_prediction_record(request_payload: dict, predicted_price_inr: float, predicted_price_jod: float) -> None:
    data_dir, history_file = _resolve_paths()
    data_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": request_payload,
        "response": {
            "predicted_price_inr": predicted_price_inr,
            "predicted_price_jod": predicted_price_jod,
        },
    }
    with history_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
