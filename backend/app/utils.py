def normalize_time(value: str) -> str:
    text = str(value).strip()
    mapping = {
        "Early Morning": "Early_Morning",
        "Morning": "Morning",
        "Afternoon": "Afternoon",
        "Evening": "Evening",
        "Night": "Night",
        "Late Night": "Late_Night",
        "Early_Morning": "Early_Morning",
        "Late_Night": "Late_Night",
    }
    if text not in mapping:
        raise ValueError("Invalid departure or arrival time.")
    return mapping[text]


def normalize_stop(value: str) -> str:
    text = str(value).strip()
    mapping = {
        "zero": "zero",
        "one": "one",
        "two_or_more": "two_or_more",
    }
    if text not in mapping:
        raise ValueError("Invalid stop value.")
    return mapping[text]


def normalize_month(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def normalize_holiday(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return "Yes" if text.lower() in {"yes", "true", "1"} else "No"


def normalize_trip_purpose(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text
