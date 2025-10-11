"""
pages/4_Analize_Automatike.py
Version: Stable & Audited Direct Audio + Analysis
Author: Protrade AI
"""

import pathlib, re, io, csv, json, streamlit as st
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from core.config import OUT_DIR
from core.analysis_llm import write_outputs_and_report
from core.config import load_openai_key
from core.drive_io import get_user_oauth_creds
from core.transcription_audio import transcribe_audio_files

st.title("🤖 Analizë Automatike – Direct Audio + Raporte")

source = st.radio("Burimi:", ["Nga Folder Lokal (TXT/DOCX)",
                              "Nga Drive (Session ID)",
                              "Direct: Nga Audio (Lokal ose nga Drive)"], index=2)

session_tag = st.text_input("Emri i sesionit për emërtimin e output-eve (opsional)", value="")
# --- Zgjedhja e gjuhës për raportin ---
lang_label = st.selectbox("Gjuha e raportit", ["Shqip","Italisht","Anglisht"], index=0)
LANG_MAP = {"Shqip": "sq", "Italisht": "it", "Anglisht": "en"}
lang_code = LANG_MAP.get(lang_label, "sq")

# --- Prompt overrides (opsionale) ---
st.caption("Instruksione shtesë për LLM (opsionale). Bëhen merge me template-in.")
summary_hint = st.text_area("Udhëzime shtesë për 'Përmbledhje' (opsionale)", value="", height=120, placeholder="p.sh., thekso tonin empatik dhe qartësinë e mbylljes; shmang fraza të përgjithshme")
bullets_hint = st.text_area("Udhëzime shtesë për 'preggi / da migliorare' (ops.)", value="", height=120, placeholder="p.sh., pregji fokus te dëgjimi aktiv; da migliorare: mbyllje e vendosur, menaxhim kundërshtish")

max_calls = st.number_input("Maksimumi i thirrjeve për t'u analizuar", 1, 5000, 100)
agent_override = st.text_input("(Opsional) Emri i agjentit për këtë ekzekutim", value="")

mapping_file = st.file_uploader("Opsional: Ngarko CSV për mapping (filename, agent, campaign)", type=["csv"])

COMMON_BAD = {"new folder","documents","downloads","desktop","vicidial_agent","data","out_analysis"}
AUDIO_EXTS = {".mp3",".wav",".m4a",".mp4",".ogg",".flac"}

def pick_agent_from_path(p: pathlib.Path) -> str:
    parts = [x.lower() for x in p.parts]
    for seg in reversed(parts):
        s = seg.replace("_"," ").strip()
        if len(s.split()) <= 3 and s not in COMMON_BAD and "." not in s:
            return s.title()
    return "UNKNOWN"

def parse_mapping_csv(buf) -> dict:
    if not buf: return {}
    text = buf.getvalue().decode("utf-8", errors="ignore")
    rdr = csv.DictReader(io.StringIO(text))
    m = {}
    for row in rdr:
        fname = (row.get("filename") or "").strip()
        if not fname: continue
        m[fname.lower()] = {
            "agent": (row.get("agent") or "").strip(),
            "campaign": (row.get("campaign") or "").strip(),
        }
    return m

# ============== UI për Direct Audio ==============
st.caption("Dërgon MP3/M4A/WAV siç janë (cilësi maksimale). Normalizon vetëm në rast gabimi, "
           "dhe përdor fallback automatik në whisper-1 nëse modeli 4o nuk pranohet.")

audio_src = st.radio("Burimi audio:", ["Lokal","Drive"], index=0, horizontal=True)
local_audio_root = None
drive_audio_session_raw = None
if audio_src == "Lokal":
    local_audio_root = st.text_input("Path lokal me audio", value=str(pathlib.Path.cwd()))
else:
    drive_audio_session_raw = st.text_input("Session Folder ID i Drive (ose URL e plotë)")

run = st.button("▶️ Transkripto + Analizo audion", type="primary",
                disabled=(audio_src=="Lokal" and not local_audio_root) or (audio_src=="Drive" and not drive_audio_session_raw))

if run:
    if not load_openai_key():
        st.error("OPENAI_API_KEY mungon.")
        st.stop()

    mapping = parse_mapping_csv(mapping_file) if mapping_file else {}
    calls = []
    progress = st.progress(0, text="Duke nisur...")
    status_box = st.empty()

    def update_prog(done:int, total:int, stage:str):
        percent = int(done/total*100) if total else 0
        progress.progress(percent, text=f"{stage}: {done}/{total} • {percent}%")

    audio_paths = []
    agent_map = {}

    # =================== BURIMI ===================
    if audio_src == "Lokal":
        root = pathlib.Path(local_audio_root)
        for p in root.rglob("*"):
            if p.suffix.lower() in AUDIO_EXTS:
                audio_paths.append(p)
                agent_map[p.stem.lower()] = pick_agent_from_path(p)
    else:
        # --- Audio nga Drive ---
        m = re.search(r"/folders/([A-Za-z0-9_-]+)", drive_audio_session_raw.strip())
        drive_session_id = m.group(1) if m else drive_audio_session_raw.strip()
        creds = get_user_oauth_creds(readonly=True)
        drive = build("drive", "v3", credentials=creds)

        def drive_list_children(service, folder_id):
            items, page_token = [], None
            while True:
                resp = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id,name,mimeType,parents)",
                    pageToken=page_token, pageSize=1000
                ).execute()
                items.extend(resp.get("files", []))
                page_token = resp.get("nextPageToken")
                if not page_token: break
            return items

        def drive_walk_audio(service, root_folder_id):
            stack = [(root_folder_id, "")]; results = []
            while stack:
                fid, prefix = stack.pop()
                for it in drive_list_children(service, fid):
                    if it["mimeType"] == "application/vnd.google-apps.folder":
                        stack.append((it["id"], f"{prefix}/{it['name']}".strip("/")))
                    else:
                        name = it["name"]
                        if any(name.lower().endswith(ext) for ext in AUDIO_EXTS):
                            results.append((it["id"], name, prefix))
            return results

        def drive_download_file(service, file_id, out_path: pathlib.Path):
            req = service.files().get_media(fileId=file_id)
            with open(out_path, "wb") as f:
                dl = MediaIoBaseDownload(f, req)
                done = False
                while not done:
                    _, done = dl.next_chunk()

        audio_items = drive_walk_audio(drive, drive_session_id)
        if not audio_items:
            st.warning("S’u gjet asnjë file audio në atë folder.")
            st.stop()
        tmpdir = pathlib.Path("tmp_drive_audio"); tmpdir.mkdir(exist_ok=True)
        total_download = min(len(audio_items), int(max_calls))
        status_box.info(f"Po shkarkoj {total_download} audio nga Drive...")
        for idx, (fid, name, folder_path) in enumerate(audio_items[:total_download], 1):
            outp = tmpdir / name
            drive_download_file(drive, fid, outp)
            audio_paths.append(outp)
            agent_guess = "UNKNOWN"
            segs = [s for s in folder_path.split("/") if s]
            if segs:
                agent_guess = segs[-1].strip().title()
            agent_map[outp.stem.lower()] = agent_guess
            update_prog(idx, total_download, "Shkarkim audio nga Drive")

    total_audio = min(len(audio_paths), int(max_calls))
    if total_audio == 0:
        st.warning("S’u gjet audio.")
        st.stop()

    # =================== TRANSKRIPTIM ===================
    session_effective = (session_tag or "").strip()
    out = transcribe_audio_files(
        audio_paths[:total_audio],
        OUT_DIR,
        session_name=session_effective or None,
        subpath="Transkripte",
        save_txt=True,
        save_docx=False,
        reuse_existing=True,
        force=False,
        keep_wav=False,
        auto_session_if_blank=True,
    )

    txts = out.get("txt_paths", [])
    status_box.info(f"U krijuan {len(txts)} transkripte (në {out.get('out_folder')}). Po përgatis analizën...")

    # =================== ANALIZA ===================
    calls = []
    for p in txts:
        agent_guess = agent_map.get(p.stem.lower(), pick_agent_from_path(p))
        campaign_guess = p.parent.name if p.parent else "UNKNOWN"
        stem = p.name.lower()
        if stem in mapping:
            agent_guess = mapping[stem].get("agent") or agent_guess
            campaign_guess = mapping[stem].get("campaign") or campaign_guess
        calls.append({
            "call_id": p.name,
            "agent": agent_override or agent_guess,
            "campaign": campaign_guess,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "duration_sec": None,
            "language": "auto",
            "transcript_path": str(p),
            "source": "local",
            "processed_at": datetime.now(timezone.utc).isoformat()
        })

    call_csv, weekly_csv, xlsx = write_outputs_and_report(
    calls,
    session_tag=(session_tag or None),
    language=lang_code,
    summary_hint=summary_hint,
    bullets_hint=bullets_hint,
)


    st.success("✅ Përfunduar.")
    col1, col2, col3 = st.columns(3)
    with open(call_csv, "rb") as f:
        col1.download_button("⬇️ call_analysis", f.read(), file_name=pathlib.Path(call_csv).name, mime="text/csv")
    with open(weekly_csv, "rb") as f:
        col2.download_button("⬇️ agent_summary_weekly", f.read(), file_name=pathlib.Path(weekly_csv).name, mime="text/csv")
    with open(xlsx, "rb") as f:
        col3.download_button("⬇️ Raport_Analize", f.read(), file_name=pathlib.Path(xlsx).name,
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # =================== AUDIT GLOBLAL ===================
    log_path = pathlib.Path("C:/vicidial_agent/out_analysis/model_usage_global.json")
    if log_path.exists():
        data = json.loads(log_path.read_text(encoding="utf-8"))
        a, b, c = data.get("gpt4o_direct", 0), data.get("gpt4o_fallback_wav", 0), data.get("whisper_fallback", 0)
        st.info(f"📊 **Model Usage:** 4o-direct={a} | 4o-fallback-wav={b} | whisper-fallback={c}")
    else:
        st.warning("Nuk u gjet ende log global (model_usage_global.json).")
