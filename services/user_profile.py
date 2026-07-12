from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_PROFILE = {
    "ankara": 2,
    "ekonomi": 2,
    "insaat": 2,
    "deprem_yapi_guvenligi": 2,
    "yazilim_ai": 2,
    "otomobil_ulasim": 1,
    "saglik_enerji": 1,
    "kultur_kitap": 1,
}


def gazette_appdata_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Gazette"
    return Path.home() / ".gazette"


def profile_path() -> Path:
    return gazette_appdata_dir() / "profile.json"


def load_profile() -> dict[str, Any]:
    path = profile_path()
    if not path.exists():
        return dict(DEFAULT_PROFILE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_PROFILE)
    profile = dict(DEFAULT_PROFILE)
    if isinstance(data, dict):
        profile.update({key: value for key, value in data.items() if key in profile})
    return profile


def save_profile(profile: dict[str, Any]) -> Path:
    path = profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = dict(DEFAULT_PROFILE)
    for key, value in profile.items():
        if key not in cleaned:
            continue
        try:
            cleaned[key] = max(0, min(3, int(value)))
        except (TypeError, ValueError):
            pass
    path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
