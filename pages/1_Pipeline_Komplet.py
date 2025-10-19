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
from core.campaign_manager import get_all_campaigns, get_campaign_hints

st.title("🤖 Analizë Automatike – Audio dhe Tekst")

# ============== SEKSIONI KRYESOR: LLOJI I BURIMIT ==============
st.subheader("📋 Lloji i burimit")
source_type = st.radio("Zgjidh llojin e burimit:", ["🎵 Audio (Transkriptim + Analizë)", "📄 Tekst (Analizë e drejtpërdrejtë)"], index=0)

# ============== PARAMETRAT E PËRBASHKËT ==============
st.subheader("⚙️ Parametrat e analizës")

# ========== ZGJEDHJA E FUSHATËS ==========
st.markdown("### 🎯 Konteksti i Fushatës")
campaigns = get_all_campaigns()
campaign_options = ["Asnjë kontekst specifik"] + [c["name"] for c in campaigns]
selected_campaign_name = st.selectbox(
    "Zgjidhni fushatën/kontekstin për analizë",
    campaign_options,
    index=0,
    help="Zgjidhni një fushatë për të përfshirë kontekst specifik dhe dokumente në analizë"
)

# Merr ID-në e fushatës së zgjedhur
selected_campaign_id = None
if selected_campaign_name != "Asnjë kontekst specifik":
    for c in campaigns:
        if c["name"] == selected_campaign_name:
            selected_campaign_id = c["id"]
            break

    # Shfaq info për fushatën e zgjedhur
    if selected_campaign_id:
        campaign_info = get_campaign_hints(selected_campaign_id)
        with st.expander("ℹ️ Shiko detajet e fushatës së zgjedhur", expanded=False):
            if campaign_info.get("project_context_hint"):
                st.caption("**Project Context:**")
                st.text(campaign_info["project_context_hint"][:200] + "..." if len(campaign_info["project_context_hint"]) > 200 else campaign_info["project_context_hint"])
            if campaign_info.get("summary_hint"):
                st.caption("**Summary Hint:**")
                st.text(campaign_info["summary_hint"][:200] + "..." if len(campaign_info["summary_hint"]) > 200 else campaign_info["summary_hint"])
            if campaign_info.get("bullets_hint"):
                st.caption("**Bullets Hint:**")
                st.text(campaign_info["bullets_hint"][:200] + "..." if len(campaign_info["bullets_hint"]) > 200 else campaign_info["bullets_hint"])
            if campaign_info.get("documents_text"):
                st.caption(f"**Dokumente:** {len(campaign_info['documents_text'])} karaktere të ngarkuara")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    session_tag = st.text_input("Emri i sesionit për emërtimin e output-eve (opsional)", value="")
    lang_label = st.selectbox("Gjuha e raportit", ["Shqip","Italisht","Anglisht"], index=0)
    LANG_MAP = {"Shqip": "sq", "Italisht": "it", "Anglisht": "en"}
    lang_code = LANG_MAP.get(lang_label, "sq")

with col2:
    max_calls = st.number_input("Maksimumi i thirrjeve për t'u analizuar", 1, 5000, 100)
    agent_override = st.text_input("(Opsional) Emri i agjentit për këtë ekzekutim", value="")

# --- Prompt overrides (opsionale) ---
st.caption("Instruksione shtesë për LLM (opsionale). Bëhen merge me template-in.")
summary_hint = st.text_area("Udhëzime shtesë për 'Përmbledhje' (opsionale)", value="", height=120, placeholder="p.sh., thekso tonin empatik dhe qartësinë e mbylljes; shmang fraza të përgjithshme")
bullets_hint = st.text_area("Udhëzime shtesë për 'preggi / da migliorare' (ops.)", value="", height=120, placeholder="p.sh., pregji fokus te dëgjimi aktiv; da migliorare: mbyllje e vendosur, menaxhim kundërshtish")

mapping_file = st.file_uploader("Opsional: Ngarko CSV për mapping (filename, agent, campaign)", type=["csv"])

# ============== SEKSIONI I AUDIO ==============
if "Audio" in source_type:
    st.subheader("🎵 Konfigurimi i Audio")

    # Burimi i audio
    audio_source = st.radio("Burimi i audio:", ["Lokal", "Drive", "Ngarko file direkt"], index=0, horizontal=True)

    # Opsionet për llojet e audio
    st.caption("Llojet e audio të mbështetura: MP3, WAV, M4A, MP4, OGG, FLAC")

    # Filtrimi i kohëzgjatjes
    st.caption("Filtrimi i kohëzgjatjes (opsional)")
    col_dur1, col_dur2 = st.columns(2)
    with col_dur1:
        min_duration = st.number_input("Kohëzgjatja minimale (sekonda)", 0, 3600, 0, help="0 = pa kufi")
    with col_dur2:
        max_duration = st.number_input("Kohëzgjatja maksimale (sekonda)", 0, 3600, 0, help="0 = pa kufi")

    # Input fields bazuar në zgjedhjen
    local_audio_root = None
    drive_audio_session_raw = None
    uploaded_files = None

    if audio_source == "Lokal":
        local_audio_root = st.text_input("Path lokal me audio", value=str(pathlib.Path.cwd()))
    elif audio_source == "Drive":
        drive_audio_session_raw = st.text_input("Session Folder ID i Drive (ose URL e plotë)")
    else:  # Ngarko file direkt
        uploaded_files = st.file_uploader("Ngarko file audio", type=["mp3", "wav", "m4a", "mp4", "ogg", "flac"], accept_multiple_files=True)

    # Butoni për audio
    run_audio = st.button("🎵 Transkripto + Analizo audion", type="primary",
                         disabled=(audio_source=="Lokal" and not local_audio_root) or
                                 (audio_source=="Drive" and not drive_audio_session_raw) or
                                 (audio_source=="Ngarko file direkt" and not uploaded_files))

# ============== SEKSIONI I TEKSTIT ==============
else:  # Tekst
    st.subheader("📄 Konfigurimi i Tekstit")

    # Burimi i tekstit
    text_source = st.radio("Burimi i tekstit:", ["Nga Folder Lokal (TXT/DOCX)", "Nga Drive (Session ID)", "Ngarko file direkt"], index=0, horizontal=True)

    # Input fields bazuar në zgjedhjen
    local_text_root = None
    drive_text_session_raw = None
    uploaded_text_files = None

    if text_source == "Nga Folder Lokal (TXT/DOCX)":
        local_text_root = st.text_input("Path lokal me file TXT/DOCX", value=str(pathlib.Path.cwd()))
    elif text_source == "Nga Drive (Session ID)":
        drive_text_session_raw = st.text_input("Session Folder ID i Drive (ose URL e plotë)")
    else:  # Ngarko file direkt
        uploaded_text_files = st.file_uploader("Ngarko file teksti", type=["txt", "docx"], accept_multiple_files=True)

    # Butoni për tekst
    run_text = st.button("📄 Analizo tekstin", type="primary",
                        disabled=(text_source=="Nga Folder Lokal (TXT/DOCX)" and not local_text_root) or
                                (text_source=="Nga Drive (Session ID)" and not drive_text_session_raw) or
                                (text_source=="Ngarko file direkt" and not uploaded_text_files))

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

# ============== EKZEKUTIMI ==============
def process_audio_files():
    """Funksion për përpunimin e file-ave audio"""
    if not load_openai_key():
        st.error("OPENAI_API_KEY mungon.")
        st.stop()

    mapping = parse_mapping_csv(mapping_file) if mapping_file else {}
    calls = []

    # UI për progresin e transkriptimit
    st.subheader("📊 Progresi i Transkriptimit")
    transcription_progress = st.progress(0)
    transcription_status = st.empty()
    transcription_details_expander = st.expander("ℹ️ Detaje (kliko për të hapur)", expanded=False)

    # UI për progresin e analizës (përdoret më vonë)
    analysis_progress = st.progress(0)
    analysis_status = st.empty()

    def update_transcription_prog(current: int, total: int):
        """Callback për azhornimin e progresit të transkriptimit"""
        percent = current / total if total else 0
        transcription_progress.progress(percent)

        # Shfaq përqindjen dhe detajet
        transcription_status.markdown(f"""
        **Progresi: {percent*100:.1f}%** ✅
        """)

        # Detajet në expander
        with transcription_details_expander:
            st.markdown(f"""
            - **Audio Total:** {total} MP3
            - **Transkripte të Krijuara:** {current} TXT
            - **Mbeten për Transkriptim:** {total - current}
            """)

    def update_analysis_prog(done:int, total:int, stage:str):
        """Callback për azhornimin e progresit të analizës"""
        percent = int(done/total*100) if total else 0
        analysis_progress.progress(percent/100, text=f"{stage}: {done}/{total} • {percent}%")

    audio_paths = []
    agent_map = {}

    # =================== BURIMI I AUDIO ===================
    if audio_source == "Lokal":
        root = pathlib.Path(local_audio_root)
        for p in root.rglob("*"):
            if p.suffix.lower() in AUDIO_EXTS:
                # Filtrimi i kohëzgjatjes (nëse është specifikuar)
                if min_duration > 0 or max_duration > 0:
                    try:
                        import librosa
                        duration = librosa.get_duration(filename=str(p))
                        if min_duration > 0 and duration < min_duration:
                            continue
                        if max_duration > 0 and duration > max_duration:
                            continue
                    except:
                        pass  # Nëse nuk mund të lexoj kohëzgjatjen, përfshij file-in

                audio_paths.append(p)
                agent_map[p.stem.lower()] = pick_agent_from_path(p)
    elif audio_source == "Drive":
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
            st.warning("S'u gjet asnjë file audio në atë folder.")
            st.stop()
        tmpdir = pathlib.Path("tmp_drive_audio"); tmpdir.mkdir(exist_ok=True)
        total_download = min(len(audio_items), int(max_calls))
        transcription_status.info(f"Po shkarkoj {total_download} audio nga Drive...")
        for idx, (fid, name, folder_path) in enumerate(audio_items[:total_download], 1):
            outp = tmpdir / name
            drive_download_file(drive, fid, outp)
            audio_paths.append(outp)
            agent_guess = "UNKNOWN"
            segs = [s for s in folder_path.split("/") if s]
            if segs:
                agent_guess = segs[-1].strip().title()
            agent_map[outp.stem.lower()] = agent_guess
            # Azhorno progresin e shkarkimit
            transcription_progress.progress(idx / total_download)
            transcription_status.info(f"Shkarkim audio: {idx}/{total_download}")
    else:  # Ngarko file direkt
        if uploaded_files:
            tmpdir = pathlib.Path("tmp_uploaded_audio"); tmpdir.mkdir(exist_ok=True)
            transcription_status.info(f"Po ruaj {len(uploaded_files)} file audio...")
            for idx, uploaded_file in enumerate(uploaded_files):
                # Ruaj file-in e ngarkuar
                file_path = tmpdir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                audio_paths.append(file_path)
                agent_map[file_path.stem.lower()] = pick_agent_from_path(file_path)
                # Azhorno progresin
                transcription_progress.progress((idx + 1) / len(uploaded_files))
                transcription_status.info(f"Ruajtje file-ash: {idx + 1}/{len(uploaded_files)}")

    total_audio = min(len(audio_paths), int(max_calls))
    if total_audio == 0:
        st.warning("S'u gjet audio.")
        st.stop()

    # =================== TRANSKRIPTIM ===================
    session_effective = (session_tag or "").strip()

    # Shfaq mesazhin fillestar
    transcription_status.info(f"Po transkriptoj {total_audio} file audio...")

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
        agent_map=agent_map,
        progress_callback=update_transcription_prog,  # <-- SHTONI CALLBACK
    )

    txts = out.get("txt_paths", [])
    transcription_status.success(f"✅ U krijuan {len(txts)} transkripte (në {out.get('out_folder')})")

    # Shfaq seksionin e analizës
    st.subheader("🤖 Progresi i Analizës")
    analysis_status.info("Po përgatis analizën...")

    # =================== ANALIZA ===================
    calls = []
    total_txts = len(txts)
    analysis_status.info(f"Po përgatis {total_txts} transkripte për analizë...")

    for idx, p in enumerate(txts):
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

        # Azhorno progresin e përgatitjes
        analysis_progress.progress((idx + 1) / total_txts)
        analysis_status.info(f"Përgatitje: {idx + 1}/{total_txts}")

    # Merr kontekstin e fushatës
    campaign_hints = get_campaign_hints(selected_campaign_id)

    # Merge hints: manual overrides kanë prioritet mbi fushatën
    final_project_hint = campaign_hints.get("project_context_hint", "")
    final_summary_hint = summary_hint if summary_hint.strip() else campaign_hints.get("summary_hint", "")
    final_bullets_hint = bullets_hint if bullets_hint.strip() else campaign_hints.get("bullets_hint", "")
    final_documents_text = campaign_hints.get("documents_text", "")

    analysis_status.info("Po analizoj me LLM...")
    call_csv, weekly_csv, xlsx = write_outputs_and_report(
        calls,
        session_tag=(session_tag or None),
        language=lang_code,
        summary_hint=final_summary_hint,
        bullets_hint=final_bullets_hint,
        project_context_hint=final_project_hint,
        documents_text=final_documents_text,
    )

    analysis_status.success("✅ Përfunduar.")
    st.success("✅ Përfunduar.")
    col1, col2, col3 = st.columns(3)
    with open(call_csv, "rb") as f:
        col1.download_button("⬇️ call_analysis", f.read(), file_name=pathlib.Path(call_csv).name, mime="text/csv")
    with open(weekly_csv, "rb") as f:
        col2.download_button("⬇️ agent_summary_weekly", f.read(), file_name=pathlib.Path(weekly_csv).name, mime="text/csv")
    with open(xlsx, "rb") as f:
        col3.download_button("⬇️ Raport_Analize", f.read(), file_name=pathlib.Path(xlsx).name,
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def process_text_files():
    """Funksion për përpunimin e file-ave teksti"""
    if not load_openai_key():
        st.error("OPENAI_API_KEY mungon.")
        st.stop()

    mapping = parse_mapping_csv(mapping_file) if mapping_file else {}
    calls = []

    # UI për progresin e përpunimit të tekstit
    st.subheader("📄 Progresi i Përpunimit të Tekstit")
    text_progress = st.progress(0)
    text_status = st.empty()
    text_details_expander = st.expander("ℹ️ Detaje (kliko për të hapur)", expanded=False)

    # UI për progresin e analizës
    analysis_progress = st.progress(0)
    analysis_status = st.empty()

    text_paths = []
    agent_map = {}

    # =================== BURIMI I TEKSTIT ===================
    if text_source == "Nga Folder Lokal (TXT/DOCX)":
        root = pathlib.Path(local_text_root)
        for p in root.rglob("*"):
            if p.suffix.lower() in {".txt", ".docx"}:
                text_paths.append(p)
                agent_map[p.stem.lower()] = pick_agent_from_path(p)
    elif text_source == "Nga Drive (Session ID)":
        # --- Tekst nga Drive ---
        m = re.search(r"/folders/([A-Za-z0-9_-]+)", drive_text_session_raw.strip())
        drive_session_id = m.group(1) if m else drive_text_session_raw.strip()
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

        def drive_walk_text(service, root_folder_id):
            stack = [(root_folder_id, "")]; results = []
            while stack:
                fid, prefix = stack.pop()
                for it in drive_list_children(service, fid):
                    if it["mimeType"] == "application/vnd.google-apps.folder":
                        stack.append((it["id"], f"{prefix}/{it['name']}".strip("/")))
                    else:
                        name = it["name"]
                        if any(name.lower().endswith(ext) for ext in [".txt", ".docx"]):
                            results.append((it["id"], name, prefix))
            return results

        def drive_download_file(service, file_id, out_path: pathlib.Path):
            req = service.files().get_media(fileId=file_id)
            with open(out_path, "wb") as f:
                dl = MediaIoBaseDownload(f, req)
                done = False
                while not done:
                    _, done = dl.next_chunk()

        text_items = drive_walk_text(drive, drive_session_id)
        if not text_items:
            st.warning("S'u gjet asnjë file teksti në atë folder.")
            st.stop()
        tmpdir = pathlib.Path("tmp_drive_text"); tmpdir.mkdir(exist_ok=True)
        total_download = min(len(text_items), int(max_calls))
        text_status.info(f"Po shkarkoj {total_download} file teksti nga Drive...")
        for idx, (fid, name, folder_path) in enumerate(text_items[:total_download], 1):
            outp = tmpdir / name
            drive_download_file(drive, fid, outp)
            text_paths.append(outp)
            agent_guess = "UNKNOWN"
            segs = [s for s in folder_path.split("/") if s]
            if segs:
                agent_guess = segs[-1].strip().title()
            agent_map[outp.stem.lower()] = agent_guess
            # Azhorno progresin e shkarkimit
            text_progress.progress(idx / total_download)
            text_status.info(f"Shkarkim teksti: {idx}/{total_download}")
    else:  # Ngarko file direkt
        if uploaded_text_files:
            tmpdir = pathlib.Path("tmp_uploaded_text"); tmpdir.mkdir(exist_ok=True)
            text_status.info(f"Po ruaj {len(uploaded_text_files)} file teksti...")
            for idx, uploaded_file in enumerate(uploaded_text_files):
                # Ruaj file-in e ngarkuar
                file_path = tmpdir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                text_paths.append(file_path)
                agent_map[file_path.stem.lower()] = pick_agent_from_path(file_path)
                # Azhorno progresin
                text_progress.progress((idx + 1) / len(uploaded_text_files))
                text_status.info(f"Ruajtje file-ash: {idx + 1}/{len(uploaded_text_files)}")

    total_text = min(len(text_paths), int(max_calls))
    if total_text == 0:
        st.warning("S'u gjet file teksti.")
        st.stop()

    # =================== ANALIZA E DIREKTË ===================
    text_status.info(f"Po përgatis {total_text} file teksti për analizë...")

    # Shfaq seksionin e analizës
    st.subheader("🤖 Progresi i Analizës")
    analysis_status.info("Po përgatis analizën...")

    calls = []
    analysis_status.info(f"Po përgatis {total_text} file teksti për analizë...")

    for idx, p in enumerate(text_paths):
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

        # Azhorno progresin e përgatitjes
        analysis_progress.progress((idx + 1) / total_text)
        analysis_status.info(f"Përgatitje: {idx + 1}/{total_text}")

    # Merr kontekstin e fushatës
    campaign_hints = get_campaign_hints(selected_campaign_id)

    # Merge hints: manual overrides kanë prioritet mbi fushatën
    final_project_hint = campaign_hints.get("project_context_hint", "")
    final_summary_hint = summary_hint if summary_hint.strip() else campaign_hints.get("summary_hint", "")
    final_bullets_hint = bullets_hint if bullets_hint.strip() else campaign_hints.get("bullets_hint", "")
    final_documents_text = campaign_hints.get("documents_text", "")

    analysis_status.info("Po analizoj me LLM...")
    call_csv, weekly_csv, xlsx = write_outputs_and_report(
        calls,
        session_tag=(session_tag or None),
        language=lang_code,
        summary_hint=final_summary_hint,
        bullets_hint=final_bullets_hint,
        project_context_hint=final_project_hint,
        documents_text=final_documents_text,
    )

    analysis_status.success("✅ Përfunduar.")
    st.success("✅ Përfunduar.")
    col1, col2, col3 = st.columns(3)
    with open(call_csv, "rb") as f:
        col1.download_button("⬇️ call_analysis", f.read(), file_name=pathlib.Path(call_csv).name, mime="text/csv")
    with open(weekly_csv, "rb") as f:
        col2.download_button("⬇️ agent_summary_weekly", f.read(), file_name=pathlib.Path(weekly_csv).name, mime="text/csv")
    with open(xlsx, "rb") as f:
        col3.download_button("⬇️ Raport_Analize", f.read(), file_name=pathlib.Path(xlsx).name,
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =================== EKZEKUTIMI ===================
if "Audio" in source_type and run_audio:
    process_audio_files()
elif "Tekst" in source_type and run_text:
    process_text_files()
