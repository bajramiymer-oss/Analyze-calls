
import os
from typing import Optional, Tuple
from urllib.parse import urljoin
import requests
from pathlib import Path
from .config import VICIDIAL_WEB

def build_recording_url(location: str) -> str:
    """Kthen URL absolute për një 'location'."""
    if location.startswith("http://") or location.startswith("https://"):
        return location
    base = VICIDIAL_WEB.rstrip("/") + "/"
    loc = location.lstrip("/")
    return urljoin(base, loc)

def download_recording(location: str, out_path: Path, auth: Optional[Tuple[str,str]] = None, timeout: int = 120) -> bool:
    url = build_recording_url(location)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, auth=auth, timeout=timeout, verify=False) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} për {url}")
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
    return out_path.exists() and out_path.stat().st_size > 0
