"""
pages/3_Transkriptim.py
Version: Stable & Audited Transcribe UI
Author: Protrade AI
"""

import streamlit as st
import pathlib, json
from core.transcription_audio import transcribe_audio_files
from core.config import OUT_DIR

st.title("📝 Transkriptim (Audio → TXT/DOCX)")
st.caption(
    "Strategjia: **Direct-first** (dërgon MP3/M4A/WAV direkt te `gpt-4o-transcribe`) → "
    "nëse ka gabim dekodimi, **fallback** automatik në WAV 16k mono → "
    "nëse modeli refuzohet, **fallback** në `whisper-1`.\n\n"
    "Në fund, shfaqet audit global i përdorimit të modeleve."
)

# ================= PARAMETRAT =================
session_name = st.text_input("Emri i sesionit (nën out_analysis/)", placeholder="p.sh. 2025-10-07_Batch1")
mode = st.radio("Mode", ["per-file", "merged"], index=0, horizontal=True)

colA, colB, colC = st.columns(3)
with colA:
    reuse_existing = st.checkbox("Përdor caching", value=True)
with colB:
    save_docx = st.checkbox("Ruaj edhe .docx", value=False)
with colC:
    force = st.checkbox("Ritranskripto nga e para (force)", value=False)

KEEP_WAV = False
AUTO_SESSION_IF_BLANK = True

# ================== UPLOAD NGA UI ==================
st.markdown("### A) Ngarko audio")
upl = st.file_uploader(
    "Zgjidh audio (MP3, WAV, M4A, OGG, FLAC)",
    type=["mp3", "wav", "m4a", "mp4", "ogg", "flac"],
    accept_multiple_files=True
)

if st.button("▶️ Transkripto të ngarkuarat", type="primary", disabled=not upl):
    tmpdir = pathlib.Path("tmp_audio")
    tmpdir.mkdir(exist_ok=True)
    paths = []
    for up in upl:
        p = tmpdir / up.name
        with open(p, "wb") as f:
            f.write(up.getbuffer())
        paths.append(p)

    st.info("⏳ Duke transkriptuar...")
    try:
        out = transcribe_audio_files(
            input_paths=paths,
            out_dir=OUT_DIR,
            session_name=session_name or None,
            subpath="Transkripte",
            save_txt=True,
            save_docx=save_docx,
            reuse_existing=reuse_existing,
            force=force,
            keep_wav=KEEP_WAV,
            auto_session_if_blank=AUTO_SESSION_IF_BLANK,
        )
        st.success(f"✅ Transkriptimi u krye për {len(out.get('txt_paths', []))} file.")
        st.info(f"📁 Folder output: {out.get('out_folder')}")
        for t in out.get("txt_paths", []):
            st.markdown(f"- {t.as_posix()}")

        # Lexo audit global
        log_path = pathlib.Path("C:/vicidial_agent/out_analysis/model_usage_global.json")
        if log_path.exists():
            data = json.loads(log_path.read_text(encoding="utf-8"))
            a, b, c = data.get("gpt4o_direct", 0), data.get("gpt4o_fallback_wav", 0), data.get("whisper_fallback", 0)
            st.info(f"📊 **Model Usage:** 4o-direct={a} | 4o-fallback-wav={b} | whisper-fallback={c}")
        else:
            st.warning("Nuk u gjet ende log global (model_usage_global.json).")

    except Exception as e:
        st.error(f"Gabim: {e}")

# ================== NGA FOLDER LOKAL ==================
st.markdown("---")
st.markdown("### B) Transkripto nga Folder Lokal")

local_root = st.text_input("Path lokal me audio", value=str(pathlib.Path.cwd()))

if st.button("▶️ Transkripto nga folderi", type="primary", disabled=not local_root):
    root = pathlib.Path(local_root)
    audio_exts = [".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".flac"]
    audio = [p for p in root.rglob("*") if p.suffix.lower() in audio_exts]
    if not audio:
        st.warning("⚠️ S’u gjet audio në këtë rrugë.")
    else:
        st.info(f"⏳ Duke përpunuar {len(audio)} audio...")
        try:
            out = transcribe_audio_files(
                input_paths=audio,
                out_dir=OUT_DIR,
                session_name=session_name or None,
                subpath="Transkripte",
                save_txt=True,
                save_docx=save_docx,
                reuse_existing=reuse_existing,
                force=force,
                keep_wav=KEEP_WAV,
                auto_session_if_blank=AUTO_SESSION_IF_BLANK,
            )
            st.success(f"✅ Transkriptimi u krye për {len(out.get('txt_paths', []))} file.")
            st.info(f"📁 Folder output: {out.get('out_folder')}")
            for t in out.get("txt_paths", []):
                st.markdown(f"- {t.as_posix()}")

            # Audit global
            log_path = pathlib.Path("C:/vicidial_agent/out_analysis/model_usage_global.json")
            if log_path.exists():
                data = json.loads(log_path.read_text(encoding="utf-8"))
                a, b, c = data.get("gpt4o_direct", 0), data.get("gpt4o_fallback_wav", 0), data.get("whisper_fallback", 0)
                st.info(f"📊 **Model Usage:** 4o-direct={a} | 4o-fallback-wav={b} | whisper-fallback={c}")
            else:
                st.warning("Nuk u gjet ende log global (model_usage_global.json).")

        except Exception as e:
            st.error(f"Gabim: {e}")
