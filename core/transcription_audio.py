"""
core/transcription_audio.py
Version: Stable & Audited Transcribe
Author: Protrade AI
"""

from __future__ import annotations
import os, json, time, subprocess, re
from pathlib import Path
from typing import List, Optional, Dict, Any
import datetime as dt

# ====================== KONFIGURIMI BAZË ======================

MODEL_PRIMARY = "gpt-4o-transcribe"
MODEL_FALLBACK = "whisper-1"
GLOBAL_LOG = Path("C:/vicidial_agent/out_analysis/model_usage_global.json")

# ===============================================================

def _get_models_from_secrets() -> str:
    """Lexon modelin nga secrets ose përdor default."""
    try:
        import streamlit as st
        model = st.secrets.get("openai", {}).get("MODEL_TRANSCRIBE", MODEL_PRIMARY)
        return model or MODEL_PRIMARY
    except Exception:
        return MODEL_PRIMARY


def _openai_client():
    """Krijon klientin OpenAI me API key nga mjedisi ose secrets."""
    from openai import OpenAI
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("openai", {}).get("OPENAI_API_KEY")
        except Exception:
            pass
    if not key:
        raise RuntimeError("OPENAI_API_KEY mungon në mjedis ose secrets.")
    return OpenAI(api_key=key)


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _ffmpeg_exists() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _normalize_to_wav(input_path: Path, out_dir: Path) -> Path:
    """Normalizon në wav 16k mono për fallback."""
    norm_path = out_dir / f"{input_path.stem}_16k.wav"
    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-ac", "1", "-ar", "16000", "-vn", str(norm_path)]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return norm_path


# ====================== FUNKSIONET KRYESORE ======================

def _transcribe_file(path: Path, model_name: str) -> str:
    """Thërret OpenAI Transcribe për një file."""
    client = _openai_client()
    for attempt in range(3):
        try:
            with open(path, "rb") as f:
                resp = client.audio.transcriptions.create(file=f, model=model_name)
            return resp.text.strip()
        except Exception as e:
            msg = str(e).lower()
            # fallback model nëse modeli s’pranohet
            if "invalid_value" in msg and model_name == MODEL_PRIMARY:
                return _transcribe_file(path, MODEL_FALLBACK)
            # retry për gabime rrjeti
            if "timeout" in msg or "connection" in msg or "service unavailable" in msg:
                time.sleep(2 + attempt)
                continue
            raise
    raise RuntimeError(f"Dështim transkriptimi pas 3 tentativash për {path.name}")


def _direct_first_with_fallback(src: Path, work_dir: Path, model_name: str, keep_wav: bool = False) -> tuple[str, str]:
    """
    Direct-first + fallback në wav dhe whisper.
    Kthen tekstin dhe emrin e modelit të përdorur.
    """
    # 1. provo direct me modelin primar
    try:
        text = _transcribe_file(src, model_name=model_name)
        return text, "gpt4o_direct"
    except Exception as e:
        msg = str(e).lower()
        # 2. nëse është error dekodimi, provo normalizim
        if any(x in msg for x in ["decode", "codec", "unsupported", "invalid audio"]):
            if _ffmpeg_exists():
                wav_path = _normalize_to_wav(src, work_dir)
                text = _transcribe_file(wav_path, model_name=model_name)
                if not keep_wav and wav_path.exists():
                    try: wav_path.unlink()
                    except Exception: pass
                return text, "gpt4o_fallback_wav"
        # 3. nëse është invalid model, provo whisper
        if "invalid_value" in msg or "bad request" in msg:
            text = _transcribe_file(src, model_name=MODEL_FALLBACK)
            return text, "whisper_fallback"
        raise


def _update_global_log(stats: Dict[str, int]):
    """Përditëson log global pas batch-it."""
    GLOBAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    if GLOBAL_LOG.exists():
        try:
            existing = json.loads(GLOBAL_LOG.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    else:
        existing = {}

    for k, v in stats.items():
        existing[k] = existing.get(k, 0) + v
    existing["last_update"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    GLOBAL_LOG.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


# ====================== FUNKSIONI PUBLIK ======================

def transcribe_audio_files(
    input_paths: List[str | Path],
    out_dir: str | Path,
    session_name: Optional[str] = None,
    subpath: Optional[str] = None,
    save_txt: bool = True,
    save_docx: bool = False,
    reuse_existing: bool = True,
    force: bool = False,
    keep_wav: bool = False,
    auto_session_if_blank: bool = True,
) -> Dict[str, Any]:
    """
    Transkripton listë audiosh me Direct-first + fallback dhe log global modeli.
    """
    model = _get_models_from_secrets()
    root = Path(out_dir)
    if auto_session_if_blank and not session_name:
        session_name = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    if session_name:
        root = root / session_name
    if subpath:
        root = root / subpath
    _ensure_dir(root)

    txt_paths: List[Path] = []
    usage = {"gpt4o_direct": 0, "gpt4o_fallback_wav": 0, "whisper_fallback": 0}

    for p in input_paths:
        src = Path(p)
        if not src.exists():
            continue

        base = root / src.stem
        txt_path = base.with_suffix(".txt")

        # caching
        if reuse_existing and not force and txt_path.exists():
            if txt_path.stat().st_mtime >= src.stat().st_mtime:
                txt_paths.append(txt_path)
                continue

        try:
            text, model_used = _direct_first_with_fallback(src, root, model_name=model, keep_wav=keep_wav)
            usage[model_used] += 1
        except Exception as e:
            print(f"[ERROR] {src.name}: {e}")
            continue

        if save_txt:
            txt_path.write_text(text, encoding="utf-8")
            txt_paths.append(txt_path)
        if save_docx:
            from docx import Document
            doc = Document()
            doc.add_paragraph(text)
            doc.save(base.with_suffix(".docx"))

    # update global log only once
    _update_global_log(usage)

    return {"txt_paths": txt_paths, "out_folder": root, "usage": usage}
