import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from backend.app.core.config import CHAT_HISTORY_FILE, DATA_DIR
except ImportError:  # pragma: no cover
    from app.core.config import CHAT_HISTORY_FILE, DATA_DIR


def save_chat_record(
    conversation_id: str,
    trip_context: dict | None,
    user_message: str,
    assistant_response: str,
) -> None:
    data_dir, history_file = _resolve_paths()
    data_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "conversation_id": conversation_id,
        "trip_context": trip_context or {},
        "user_message": user_message,
        "assistant_response": assistant_response,
    }
    with history_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _resolve_paths() -> tuple[Path, Path]:
    try:
        import backend.main as main_module
    except Exception:  # pragma: no cover
        return Path(DATA_DIR), Path(CHAT_HISTORY_FILE)
    return Path(getattr(main_module, "DATA_DIR", DATA_DIR)), Path(getattr(main_module, "CHAT_HISTORY_FILE", CHAT_HISTORY_FILE))
