"""
core/mobile_fix_classifier.py

PURPOSE:
    Classify phone numbers as Mobile or Fix based on Italian prefixes
    and calculate VoIP costs accordingly.

CONTEXT:
    - Mobile costs: €0.0105/min (3.3x more than fix)
    - Fix costs: €0.0032/min
    - Fix numbers have province info
    - Mobile numbers don't have province (harder to segment)

Author: Protrade AI
Last Updated: 2025-10-14
"""

from typing import Tuple, Optional, Dict, List
import json
from pathlib import Path

# VoIP Costs (€/minute)
MOBILE_COST_PER_MIN = 0.0105
FIX_COST_PER_MIN = 0.0032

# Italian Mobile Prefixes (3XX)
ITALIAN_MOBILE_PREFIXES = {
    "320", "322", "323", "324", "327", "328", "329",  # Wind
    "330", "331", "333", "334", "335", "336", "337", "338", "339",  # TIM
    "340", "342", "343", "344", "345", "346", "347", "348", "349",  # Vodafone
    "350", "351", "360", "363", "366", "368",  # Altri
    "370", "373", "377", "380", "383", "388", "389",  # Altri
    "390", "391", "392", "393", "397", "398", "399"   # Altri
}

# Italian Fix Prefixes (0X, 0XX)
# Loaded from data/italian_prefixes.json if available
ITALIAN_FIX_PREFIXES = {}  # Will be populated from JSON
VALID_PROVINCES = []  # Will be populated from JSON

def load_italian_prefix_data():
    """
    Carica i dati dei prefissi italiani da data/italian_prefixes.json

    Returns:
        Dict[str, dict]: {prefix: {"province": "XX", "zone": "City"}}
    """
    global ITALIAN_FIX_PREFIXES, VALID_PROVINCES

    prefix_file = Path("data/italian_prefixes.json")
    if not prefix_file.exists():
        return {}

    try:
        with open(prefix_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            ITALIAN_FIX_PREFIXES = data.get("prefixes", {})
            VALID_PROVINCES = data.get("valid_provinces", [])
    except Exception:
        pass

    return ITALIAN_FIX_PREFIXES

# Load on import
load_italian_prefix_data()


def classify_phone_number(phone: str, lead_province: str = None) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Classifica un numero come Mobile o Fix e ritorna provincia/zona.

    LOGJIKA E RE:
    1. PËR NUMRAT FIX: Kontrollo vetëm prefix në CSV
       - Nëse gjen match → Përdor provincën nga CSV
       - Nëse nuk gjen → "UNKNOWN FIX"

    2. PËR NUMRAT MOBILE: Kontrollo fillimisht Vicidial
       - Nëse ka provincë në Vicidial → Përdor atë
       - Nëse nuk ka → "UNKNOWN MOBILE"

    3. PËR NUMRAT E TJERË: "UNKNOWN"

    Args:
        phone: Numero di telefono (es. "0612345678", "3331234567")
        lead_province: Provincia nga Vicidial Lead Information (vetëm për mobile)

    Returns:
        Tuple[type, province, zone]:
            - type: "MOBILE", "FIX", ose "UNKNOWN"
            - province: "RM", "MI", "UNKNOWN FIX", "UNKNOWN MOBILE", "UNKNOWN"
            - zone: Nome zona/città (vetëm për FIX me prefix në CSV)

    Example:
        >>> classify_phone_number("0612345678")
        ("FIX", "RM", "Roma")  # Prefix në CSV

        >>> classify_phone_number("0999999999")
        ("FIX", "UNKNOWN FIX", None)  # Nuk gjen prefix

        >>> classify_phone_number("3331234567", "MI")
        ("MOBILE", "MI", None)  # Provincë nga Vicidial

        >>> classify_phone_number("3331234567")
        ("MOBILE", "UNKNOWN MOBILE", None)  # Nuk ka provincë

        >>> classify_phone_number("1234567890")
        ("UNKNOWN", "UNKNOWN", None)  # Numër i panjohur
    """
    phone = phone.strip()

    # Heq kodin e vendit pa hequr 0-në e prefiksit fiks
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith("0039"):
        phone = phone[4:]
    elif phone.startswith("39") and len(phone) > 2:
        phone = phone[2:]

    if not phone:
        return ("UNKNOWN", "UNKNOWN", None)

    # 1. KONTROLLO NUMRAT FIX (0X, 0XX, 0XXX)
    if phone.startswith("0"):
        # Try progressively longer prefixes
        for length in [4, 3, 2]:
            prefix = phone[:length]
            if prefix in ITALIAN_FIX_PREFIXES:
                info = ITALIAN_FIX_PREFIXES[prefix]
                return ("FIX", info.get("province"), info.get("zone"))

        # Nuk gjen prefix në CSV
        return ("FIX", "UNKNOWN FIX", None)

    # 2. KONTROLLO NUMRAT MOBILE (3XX)
    if phone.startswith("3") and len(phone) == 10:
        prefix_3 = phone[:3]
        if prefix_3 in ITALIAN_MOBILE_PREFIXES:
            # Kontrollo fillimisht provincën nga Vicidial
            if lead_province and lead_province.strip():
                # Validon nëse provinca është sigel e vlefshme
                if lead_province.strip().upper() in VALID_PROVINCES:
                    return ("MOBILE", lead_province.strip().upper(), None)
                else:
                    # Nëse nuk është sigel e vlefshme (p.sh. "Tiramisu")
                    return ("MOBILE", "UNKNOWN MOBILE", None)
            else:
                return ("MOBILE", "UNKNOWN MOBILE", None)

    # 3. NUMRAT E TJERË
    return ("UNKNOWN", "UNKNOWN", None)


def calculate_voip_cost(
    phone_type: str,
    duration_seconds: int
) -> float:
    """
    Calcola il costo VoIP per una chiamata.

    Args:
        phone_type: "MOBILE" o "FIX"
        duration_seconds: Durata in secondi

    Returns:
        float: Costo in Euro

    Example:
        >>> # 180 sec call to mobile
        >>> calculate_voip_cost("MOBILE", 180)
        0.0315  # €0.0105/min × 3 min

        >>> # 180 sec call to fix
        >>> calculate_voip_cost("FIX", 180)
        0.0096  # €0.0032/min × 3 min
    """
    minutes = duration_seconds / 60.0

    if phone_type == "MOBILE":
        return round(minutes * MOBILE_COST_PER_MIN, 6)
    elif phone_type == "FIX":
        return round(minutes * FIX_COST_PER_MIN, 6)
    else:
        # Use average of mobile and fix
        avg_cost = (MOBILE_COST_PER_MIN + FIX_COST_PER_MIN) / 2
        return round(minutes * avg_cost, 6)


def get_cost_savings_potential(
    total_mobile_minutes: float,
    total_fix_minutes: float,
    potential_shift_percentage: float = 0.10
) -> Dict[str, float]:
    """
    Calcola il risparmio potenziale spostando chiamate da mobile a fix.

    Args:
        total_mobile_minutes: Minuti totali su mobile
        total_fix_minutes: Minuti totali su fix
        potential_shift_percentage: % di chiamate mobile che potrebbero essere fix

    Returns:
        Dict con savings analysis

    Example:
        >>> get_cost_savings_potential(10000, 15000, 0.10)
        {
            "current_mobile_cost": 105.0,
            "current_fix_cost": 48.0,
            "total_current_cost": 153.0,
            "potential_savings_per_day": 7.30,
            "potential_savings_per_month": 219.0
        }
    """
    current_mobile_cost = total_mobile_minutes * MOBILE_COST_PER_MIN
    current_fix_cost = total_fix_minutes * FIX_COST_PER_MIN
    total_current = current_mobile_cost + current_fix_cost

    # If we shift X% from mobile to fix
    shiftable_minutes = total_mobile_minutes * potential_shift_percentage
    savings_per_minute = MOBILE_COST_PER_MIN - FIX_COST_PER_MIN
    daily_savings = shiftable_minutes * savings_per_minute

    return {
        "current_mobile_cost": round(current_mobile_cost, 2),
        "current_fix_cost": round(current_fix_cost, 2),
        "total_current_cost": round(total_current, 2),
        "shiftable_minutes": round(shiftable_minutes, 2),
        "potential_savings_per_day": round(daily_savings, 2),
        "potential_savings_per_month": round(daily_savings * 30, 2)
    }


def analyze_prefix_performance(prefix_data: list) -> Dict:
    """
    Analizon performance sipas prefix për të identifikuar best zones.

    Args:
        prefix_data: List of dicts from vicidial_log grouped by prefix
            [{"prefix_3": "010", "calls": 1000, "svyclm": 50, ...}, ...]

    Returns:
        Dict me analiza dhe rekomandime
    """
    mobile_prefixes = []
    fix_prefixes = []

    for item in prefix_data:
        prefix = item.get("prefix_3", "")
        calls = item.get("calls", 0)

        if prefix.startswith("3"):
            mobile_prefixes.append(item)
        elif prefix.startswith("0"):
            fix_prefixes.append(item)

    # Sort by performance (e.g., SVYCLM rate or conversion)
    # This will be expanded based on actual data

    return {
        "mobile_count": len(mobile_prefixes),
        "fix_count": len(fix_prefixes),
        "total_mobile_calls": sum(p.get("calls", 0) for p in mobile_prefixes),
        "total_fix_calls": sum(p.get("calls", 0) for p in fix_prefixes),
        "top_mobile_prefixes": sorted(mobile_prefixes, key=lambda x: x.get("calls", 0), reverse=True)[:10],
        "top_fix_prefixes": sorted(fix_prefixes, key=lambda x: x.get("calls", 0), reverse=True)[:10]
    }

