import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


CONFIG_DIR = Path.cwd() / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.json"


DEFAULT_STATUS_COSTS: Dict[str, float] = {
    "NA": 0.0,
    "PU": 0.0,
    "SVYCLM": 0.0,
    "BUSY": 0.0,
    "DROP": 0.0,
    "AMD": 0.0,
}

DEFAULT_DIAL_STATUSES = ["PU","SVYCLM"]


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_settings() -> Dict[str, Any]:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _write_settings(data: Dict[str, Any]) -> None:
    _ensure_dir()
    SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_status_cost_map() -> Dict[str, float]:
    data = _read_settings()
    raw = data.get("status_cost_map") or {}
    out: Dict[str, float] = {**DEFAULT_STATUS_COSTS}
    for k, v in raw.items():
        try:
            out[str(k)] = float(v)
        except Exception:
            continue
    # Ensure non-negative and max 1.0
    for k, v in list(out.items()):
        out[k] = float(max(0.0, min(1.0, v)))
    return out


def update_status_cost_map(new_map: Dict[str, float]) -> Dict[str, float]:
    data = _read_settings()
    cleaned: Dict[str, float] = {}
    for k, v in (new_map or {}).items():
        try:
            val = float(v)
        except Exception as e:
            raise ValueError(f"Vlera për statusin {k!r} duhet të jetë numër.") from e
        if val < 0 or val > 1.0:
            raise ValueError("Kostoja për statusin duhet të jetë ndër 0.0 dhe 1.0 € / thirrje.")
        cleaned[str(k).strip().upper()] = round(val, 6)
    data["status_cost_map"] = cleaned
    data["updated_at"] = _now_iso()
    _write_settings(data)
    return get_status_cost_map()


def get_resa_threshold_percent() -> float:
    data = _read_settings()
    try:
        v = float(data.get("resa_threshold", 2.0))
        return max(0.0, min(100.0, v))
    except Exception:
        return 2.0


def update_resa_threshold_percent(v: float) -> float:
    try:
        val = float(v)
    except Exception as e:
        raise ValueError("resa_threshold duhet të jetë numër.") from e
    if val < 0.0 or val > 100.0:
        raise ValueError("resa_threshold duhet të jetë ndër 0.0 dhe 100.0%.")
    data = _read_settings()
    data["resa_threshold"] = round(val, 3)
    data["updated_at"] = _now_iso()
    _write_settings(data)
    return data["resa_threshold"]


def get_dial_statuses_for_dials() -> list[str]:
    data = _read_settings()
    vals = data.get("dial_statuses_for_dials")
    if not isinstance(vals, list) or not vals:
        return list(DEFAULT_DIAL_STATUSES)
    out = []
    for s in vals:
        s2 = str(s).strip().upper()
        if s2:
            out.append(s2)
    return out or list(DEFAULT_DIAL_STATUSES)


def update_dial_statuses_for_dials(statuses: list[str]) -> list[str]:
    if not isinstance(statuses, list):
        raise ValueError("dial_statuses_for_dials duhet të jetë listë.")
    cleaned = []
    for s in statuses:
        s2 = str(s).strip().upper()
        if s2:
            cleaned.append(s2)
    data = _read_settings()
    data["dial_statuses_for_dials"] = cleaned
    data["updated_at"] = _now_iso()
    _write_settings(data)
    return get_dial_statuses_for_dials()


def get_min_dials_per_list() -> int:
    data = _read_settings()
    try:
        v = int(data.get("min_dials_per_list", 100))
        return max(0, v)
    except Exception:
        return 100


def get_bucket_min_dials() -> int:
    data = _read_settings()
    try:
        v = int(data.get("bucket_min_dials", 30))
        return max(0, v)
    except Exception:
        return 30


def get_allow_all_statuses() -> bool:
    data = _read_settings()
    v = data.get("allow_all_statuses")
    # Default to False so filtered statuses from settings are used unless explicitly set to ALL
    return bool(v) if v is not None else False


def update_allow_all_statuses(v: bool) -> bool:
    data = _read_settings()
    data["allow_all_statuses"] = bool(v)
    data["updated_at"] = _now_iso()
    _write_settings(data)
    return get_allow_all_statuses()


# Optional SVYCLM settings
def get_svyclm_timeout_sec() -> int:
    data = _read_settings()
    try:
        return max(1, int(data.get("svyclm_timeout_sec", 20)))
    except Exception:
        return 20


def get_svyclm_timeout_ratio_warn() -> float:
    data = _read_settings()
    try:
        v = float(data.get("svyclm_timeout_ratio_warn", 0.4))
        return max(0.0, min(1.0, v))
    except Exception:
        return 0.4


# ================== Network Limits (persistent) ==================
def get_network_limits() -> Dict[str, int]:
    """Lexon limitet e rrjetit nga config/settings.json.

    Returns:
        {
          "max_parallel_downloads": int,  # default 3
          "throttle_kbps": int            # default 0 (pa throttling)
        }
    """
    data = _read_settings()
    try:
        mpd = int(data.get("network_max_parallel_downloads", 3))
    except Exception:
        mpd = 3
    try:
        thr = int(data.get("network_throttle_kbps", 0))
    except Exception:
        thr = 0
    return {"max_parallel_downloads": max(1, mpd), "throttle_kbps": max(0, thr)}


def update_network_limits(max_parallel_downloads: int, throttle_kbps: int) -> Dict[str, int]:
    """Përditëson limitet e rrjetit në config/settings.json.

    Args:
        max_parallel_downloads: numri maksimal i shkarkimeve paralele (>=1)
        throttle_kbps: kufiri i shpejtësisë në KB/s (0 = pa limit)

    Returns:
        dict: vlerat e ruajtura
    """
    if max_parallel_downloads < 1:
        raise ValueError("max_parallel_downloads duhet të jetë ≥ 1")
    if throttle_kbps < 0:
        raise ValueError("throttle_kbps nuk mund të jetë negativ")
    data = _read_settings()
    data["network_max_parallel_downloads"] = int(max_parallel_downloads)
    data["network_throttle_kbps"] = int(throttle_kbps)
    data["updated_at"] = _now_iso()
    _write_settings(data)
    return get_network_limits()

