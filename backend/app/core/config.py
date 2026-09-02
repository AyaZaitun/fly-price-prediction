import os
from pathlib import Path

def load_environment() -> None:
    candidates = (
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    )
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = [part.strip() for part in stripped.split("=", 1)]
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


load_environment()

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
MODEL_DIR = BACKEND_DIR / "model"
PREDICTION_HISTORY_FILE = DATA_DIR / "prediction_history.jsonl"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.jsonl"
LLM_URL = os.getenv("LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "25"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    ).split(",")
    if origin.strip()
]
