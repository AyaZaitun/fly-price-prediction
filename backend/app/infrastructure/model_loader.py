from pathlib import Path

import joblib

try:
    from backend.app.core.config import MODEL_DIR, PROJECT_DIR
except ImportError:  # pragma: no cover
    from app.core.config import MODEL_DIR, PROJECT_DIR

MODEL_CANDIDATES = [
    MODEL_DIR / "flight_XGB_pipeline.pkl",
    MODEL_DIR / "random_forest_pipeline.pkl",
    PROJECT_DIR / "random_forest_pipeline.pkl",
]
MODEL_PATH = next((path for path in MODEL_CANDIDATES if path.exists()), MODEL_CANDIDATES[0])
_model = None


def load_model():
    global _model
    if _model is not None:
        return _model
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found. Looked for: {[str(path) for path in MODEL_CANDIDATES]}")
    _model = joblib.load(MODEL_PATH)
    return _model


def get_model():
    return load_model()
