
import os
from typing import Optional, Tuple
from urllib.parse import urljoin
import requests
from pathlib import Path
from .config import VICIDIAL_WEB, get_network_limits

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
    limits = get_network_limits()
    throttle_kbps = max(0, int(limits.get("throttle_kbps", 0)))
    chunk_size = 1024 * 256  # 256KB default
    if throttle_kbps and throttle_kbps > 0:
        # Adjust chunk size to approximate throttle
        # e.g., 256KB per read ~ throttle step
        chunk_size = int((throttle_kbps * 1024) / 4)  # 4 reads per second approx
        if chunk_size < 16 * 1024:
            chunk_size = 16 * 1024
    with requests.get(url, stream=True, auth=auth, timeout=timeout, verify=False) as r:
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} për {url}")
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    return out_path.exists() and out_path.stat().st_size > 0
