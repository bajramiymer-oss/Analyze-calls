import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CONFIG_DIR = Path.cwd() / "config"
VOIP_RATES_PATH = CONFIG_DIR / "voip_rates.json"


@dataclass
class VoipRates:
    mobile_eur_per_min: float
    fix_eur_per_min: float
    updated_at: str


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def get_voip_rates() -> VoipRates:
    """Read VoIP rates from config/voip_rates.json; fallback to sensible defaults.

    Returns a VoipRates dataclass. Defaults: mobile 0.060, fix 0.020.
    """
    try:
        if VOIP_RATES_PATH.exists():
            data = json.loads(VOIP_RATES_PATH.read_text(encoding="utf-8"))
            m = float(data.get("mobile_eur_per_min", 0.060))
            f = float(data.get("fix_eur_per_min", 0.020))
            ts = str(data.get("updated_at") or _now_iso())
            return VoipRates(mobile_eur_per_min=m, fix_eur_per_min=f, updated_at=ts)
    except Exception:
        # On any parsing/validation error, fall back to defaults
        pass
    return VoipRates(mobile_eur_per_min=0.060, fix_eur_per_min=0.020, updated_at=_now_iso())


def update_voip_rates(rates: dict) -> VoipRates:
    """Validate and persist rates to JSON; returns persisted VoipRates.

    Expected keys: mobile_eur_per_min, fix_eur_per_min (floats, 0 < rate <= 2.0)
    """
    def _validate(name: str, value: float) -> float:
        try:
            v = float(value)
        except Exception as e:
            raise ValueError(f"{name} duhet të jetë numër.") from e
        if not (v > 0.0 and v <= 2.0):
            raise ValueError(f"{name} jashtë intervalit të lejuar (0 < v <= 2.0).")
        return round(v, 6)

    mobile = _validate("mobile_eur_per_min", rates.get("mobile_eur_per_min"))
    fix = _validate("fix_eur_per_min", rates.get("fix_eur_per_min"))
    _ensure_config_dir()
    payload = {
        "mobile_eur_per_min": mobile,
        "fix_eur_per_min": fix,
        "updated_at": _now_iso(),
    }
    VOIP_RATES_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return VoipRates(mobile_eur_per_min=mobile, fix_eur_per_min=fix, updated_at=payload["updated_at"])



