import os
from pathlib import Path

import joblib

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
MODEL_CANDIDATES = [
    BACKEND_DIR / "model" / "random_forest_pipeline.pkl",
    ROOT_DIR / "random_forest_pipeline.pkl",
]
MODEL_PATH = next((path for path in MODEL_CANDIDATES if path.exists()), MODEL_CANDIDATES[0])
_model = None


def load_model():
    global _model
    if _model is not None:
        return _model
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Model file not found at backend/model/random_forest_pipeline.pkl or project root/random_forest_pipeline.pkl")
    _model = joblib.load(MODEL_PATH)
    return _model


def get_model():
    return load_model()
