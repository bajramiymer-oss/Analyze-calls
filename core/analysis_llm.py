# core/analysis_llm.py
# Version: Unified Prompt + Template override + Safe template rendering + Language & UI overrides
from __future__ import annotations

import os, json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI

from core.config import OUT_DIR
from core.reporting_excel import write_excel_report_textual

# ============ Config ============
DEFAULT_MODEL = "gpt-4.1"
TEMPLATE_PATH = Path("C:/vicidial_agent/core/prompt_analysis_template.txt")

# Prompt fallback (Versioni 1, pa numra)
DEFAULT_PROMPT = """Ti je analist i cilësisë së komunikimit për telefonata shërbimi/shitjeje. Prodhon një raport të shkurtër, profesional dhe plotësisht në {language_name}, pa përdorur vlera numerike. Fokusi: ton, qartësi, strukturë dhe ndikim i komunikimit.

Udhëzime:
- PËRMBLEDHJE: stil menaxherial, i përmbajtur, analitik dhe jo përsëritës. Mos ripërsërit gjërat që do shfaqen te “preggi/da migliorare”. Ton profesional dhe njerëzor.
- PREGGI: 3–5 pika të qarta, konkrete, pozitive (jo metrikë).
- DA MIGLIORARE: 3–5 pika të qarta, konkrete, konstruktive (jo metrikë).
- Mos përdor vlera numerike. Shkruaj në {language_name}.

EXTRA-INSTRUKSIONE-PËRMBLEDHJE (opsionale):
{summary_hint}

EXTRA-INSTRUKSIONE-PIKAT (opsionale):
{bullets_hint}

Kthe vetëm JSON me skemën:
{{
  "agent": "<emri i agjentit>",
  "summary": "<paragraf i vetëm (stil Versioni 1, pa numra)>",
  "preggi": ["<pikë>", "<pikë>", "<pikë>"],
  "da_migliorare": ["<pikë>", "<pikë>", "<pikë>"]
}}

Kontekst:
- Agjenti: {agent_name}
- Transkript (një ose disa telefonata të fundit):
<<<TRANSCRIPT>>>
{transcript_text}
<<<END>>>
"""

# ============ Utils ============
def _load_model_from_secrets() -> str:
    try:
        import streamlit as st
        m = st.secrets.get("openai", {}).get("MODEL_ANALYSIS", DEFAULT_MODEL)
        return m or DEFAULT_MODEL
    except Exception:
        return DEFAULT_MODEL

def _load_template() -> str:
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    return DEFAULT_PROMPT

def _get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("openai", {}).get("OPENAI_API_KEY")
        except Exception:
            pass
    if not key:
        raise RuntimeError("OPENAI_API_KEY mungon.")
    return OpenAI(api_key=key)

def _coerce_json(s: str) -> Dict[str, Any]:
    if not s:
        return {"agent": "", "summary": "", "preggi": [], "da_migliorare": []}
    s = s.strip()
    s = s.replace("```json", "").replace("```", "").strip()
    start = s.find("{"); end = s.rfind("}")
    if start != -1 and end != -1:
        s = s[start:end+1]
    try:
        return json.loads(s)
    except Exception:
        return {"agent": "", "summary": s, "preggi": [], "da_migliorare": []}

def _render_template_safely(tmpl_raw: str, **kwargs) -> str:
    """
    Escapo të gjitha kllapat përveç placeholder-ëve që kemi në kwargs.
    """
    esc = tmpl_raw.replace("{", "{{").replace("}", "}}")
    # rikthe vetëm placeholder-ët që duam të zëvendësojmë
    for k in kwargs.keys():
        esc = esc.replace("{{" + k + "}}", "{" + k + "}")
    return esc.format(**kwargs)

def _lang_name(code: str) -> str:
    return {"sq": "shqip", "it": "italisht", "en": "anglisht"}.get(code, "shqip")

# ============ LLM ============
def analyze_agent_transcripts(
    agent_name: str,
    transcript_text: str,
    model: Optional[str]=None,
    language: str="sq",
    summary_hint: str="",
    bullets_hint: str="",
) -> Dict[str, Any]:
    """
    Kthen dict:
      {
        "agent": str,
        "summary": str,
        "preggi": [str...],
        "da_migliorare": [str...]
      }
    Gjithçka në gjuhën e zgjedhur, pa numra.
    """
    client = _get_client()
    tmpl = _load_template()
    prompt = _render_template_safely(
        tmpl_raw=tmpl,
        agent_name=agent_name,
        transcript_text=transcript_text[:50_000],
        language_name=_lang_name(language),
        summary_hint=(summary_hint or "").strip(),
        bullets_hint=(bullets_hint or "").strip(),
    )

    model = model or _load_model_from_secrets()
    sys_lang = {
        "sq": "Puno vetëm në SHQIP. Mos përdor numra në tekst.",
        "it": "Lavora solo in ITALIANO. Non usare numeri nel testo.",
        "en": "Work only in ENGLISH. Do not use numeric values in the text."
    }.get(language, "Puno vetëm në SHQIP. Mos përdor numra në tekst.")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": f"Ti je një analist komunikimi. {sys_lang}"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    content = resp.choices[0].message.content or ""
    data = _coerce_json(content)

    # Normalizim minimal
    data["agent"] = (data.get("agent") or agent_name).strip()
    data["summary"] = (data.get("summary") or "").strip()
    data["preggi"] = [p.strip("• ").strip() for p in (data.get("preggi") or []) if p and p.strip()]
    data["da_migliorare"] = [p.strip("• ").strip() for p in (data.get("da_migliorare") or []) if p and p.strip()]

    # Siguro 3-5 pika në secilin seksion
    def _pad(lst, seed):
        L = lst[:]
        for x in seed:
            if len(L) >= 3: break
            if x not in L:
                L.append(x)
        return L[:5]

    data["preggi"] = _pad(data["preggi"], [
        "Ton i qëndrueshëm dhe i sjellshëm gjatë gjithë bisedës",
        "Qartësi në shpjegimin e ofertës pa e ngarkuar klientin",
        "Ritëm i përshtatur me reagimin e klientit",
    ])
    data["da_migliorare"] = _pad(data["da_migliorare"], [
        "Theksim më i qartë i përfitimeve komerciale",
        "Mbyllje më e vendosur me nxitje të qartë për veprim",
        "Menaxhim më aktiv i kundërshtive me shembuj të shkurtër",
    ])

    return data

# ============ Batch API ============

def analyze_calls_grouped_by_agent(
    rows: List[Dict[str, Any]],
    language: str="sq",
    summary_hint: str="",
    bullets_hint: str="",
) -> List[Dict[str, Any]]:
    """
    rows: [{ "agent": ..., "transcript_path": ..., ...}, ...]
    """
    from pathlib import Path
    by_agent: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        ag = (r.get("agent") or "UNKNOWN").strip() or "UNKNOWN"
        by_agent.setdefault(ag, []).append(r)

    analyzed: List[Dict[str, Any]] = []
    for agent, items in by_agent.items():
        transcripts: List[str] = []
        for it in items:
            p = Path(it.get("transcript_path", ""))
            if p.exists():
                try:
                    transcripts.append(p.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    pass
        joined = "\n\n---\n\n".join(transcripts)
        data = analyze_agent_transcripts(
            agent_name=agent,
            transcript_text=joined,
            language=language,
            summary_hint=summary_hint,
            bullets_hint=bullets_hint,
        )
        for it in items:
            analyzed.append({
                "call_id": it.get("call_id"),
                "agent": agent,
                "campaign": it.get("campaign") or "UNKNOWN",
                "summary": data["summary"],
                "preggi": " • ".join(data["preggi"]),
                "da_migliorare": " • ".join(data["da_migliorare"]),
                "transcript_path": it.get("transcript_path"),
                "processed_at": it.get("processed_at"),
                "source": it.get("source") or "local",
            })

    return analyzed

# ============ Shkrimi i output-eve ============
import csv

def _session_tagged_name(base: str, session_tag: Optional[str]) -> str:
    if session_tag:
        stem, ext = os.path.splitext(base)
        return f"{stem}_{session_tag}{ext}"
    return base

def write_outputs_and_report(
    rows: List[Dict[str, Any]],
    session_tag: Optional[str] = None,
    language: str = "sq",
    summary_hint: str = "",
    bullets_hint: str = "",
):
    """
    Shkruan:
      - call_analysis_[session].csv
      - agent_summary_weekly_[session].csv
      - Raport_Analize_[session].xlsx
    """
    analyzed_rows = analyze_calls_grouped_by_agent(
        rows,
        language=language,
        summary_hint=summary_hint,
        bullets_hint=bullets_hint,
    )

    out_root = Path(OUT_DIR); out_root.mkdir(parents=True, exist_ok=True)

    call_csv = out_root / _session_tagged_name("call_analysis.csv", session_tag)
    with call_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "call_id","agent","campaign","summary","preggi","da_migliorare","transcript_path","processed_at","source"
        ])
        w.writeheader()
        for r in analyzed_rows:
            w.writerow(r)

    weekly_csv = out_root / _session_tagged_name("agent_summary_weekly.csv", session_tag)
    with weekly_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["agent","summary","preggi","da_migliorare"])
        w.writeheader()
        seen = set()
        for r in analyzed_rows:
            k = r["agent"]
            if k in seen: continue
            seen.add(k)
            w.writerow({
                "agent": r["agent"],
                "summary": r["summary"],
                "preggi": r["preggi"],
                "da_migliorare": r["da_migliorare"],
            })

    # Excel sipas formatit ekzistues
    xlsx = out_root / _session_tagged_name("Raport_Analize.xlsx", session_tag)
    write_excel_report_textual(analyzed_rows, xlsx)
    return str(call_csv), str(weekly_csv), str(xlsx)
