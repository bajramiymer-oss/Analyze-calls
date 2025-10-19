import csv
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple


DATA_DIR = Path.cwd() / "data"
TXT_PATH = DATA_DIR / "it_prefixes.txt"
CSV_PATH = DATA_DIR / "it_prefixes.csv"


@lru_cache(maxsize=1)
def load_prefix_map() -> list[tuple[str, str, str]]:
    """Load list of (prefix, city, provincia) sorted by desc prefix length.

    Preferred source: data/it_prefixes.txt with lines:
      prefix,provincia
    or whitespace-separated: prefix provincia

    Fallback: data/it_prefixes.csv with columns: prefix,city,provincia
    """
    items: list[tuple[str, str, str]] = []

    # Preferred: TXT
    if TXT_PATH.exists():
        with open(TXT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                # Accept comma or whitespace separator
                if "," in s:
                    parts = [x.strip() for x in s.split(",")]
                else:
                    parts = s.split()
                if len(parts) >= 2:
                    prefix, prov = parts[0], parts[1]
                    if prefix:
                        items.append((prefix, "", prov))
        items.sort(key=lambda x: len(x[0]), reverse=True)
        return items

    # Fallback: CSV
    if CSV_PATH.exists():
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                p = (row.get("prefix") or "").strip()
                if not p:
                    continue
                city = (row.get("city") or "").strip()
                prov = (row.get("provincia") or "").strip()
                items.append((p, city, prov))
    # sort by longest prefix first for greedy match
    items.sort(key=lambda x: len(x[0]), reverse=True)
    return items


def normalize_it_number(num: str) -> str:
    s = (num or "").strip()
    s = s.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if s.startswith("+39"):
        s = s[3:]
    if s.startswith("0039"):
        s = s[4:]
    # keep leading zero for fixed lines
    return s


def match_prefix(num: str) -> Optional[Tuple[str, str, str]]:
    """Return (prefix, city, provincia) best match for normalized number."""
    s = normalize_it_number(num)
    for p, city, prov in load_prefix_map():
        if s.startswith(p):
            return p, city, prov
    return None



