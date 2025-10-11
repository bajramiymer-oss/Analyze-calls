import os, sys, shutil, pathlib, io, csv, re, time
from datetime import datetime, timezone, timedelta
import streamlit as st

# --- Imports from core ---
from core.config import OUT_DIR
from core.transcription_audio import transcribe_audio_files
from core.analysis_llm import write_outputs_and_report
from core.drive_io import get_user_oauth_creds
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="Vicidial – Analizë Telefonatash", page_icon="☎️", layout="wide")
st.title("☎️ Vicidial – Analizë Telefonatash (Home)")

st.markdown("""
Ky është paneli kryesor me kontroll paraprak paketash, dhe **One‑Click Pipeline**:
**Audio → Transkriptim → Analizë → Raport** (me tag sesioni dhe caching).
""")

# ---------------- Package / Env checks ----------------
def check_pkg(name):
    try:
        __import__(name)
        return True, ""
    except Exception as e:
        return False, str(e)

checks = {}
for pkg in ["openpyxl", "pymysql", "docx", "requests", "googleapiclient", "google_auth_oauthlib", "openai"]:
    ok, err = check_pkg(pkg if pkg != "docx" else "docx")
    checks[pkg] = (ok, err)

def ffmpeg_in_path():
    import subprocess
    try:
        p = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.returncode == 0
    except Exception:
        return False

with st.expander("🩺 Kontroll paraprak (paketa & mjedisi)"):
    cols = st.columns(3)
    pkgs = list(checks.items())
    for i, (name, (ok, err)) in enumerate(pkgs):
        with cols[i % 3]:
            st.write(("✅" if ok else "❌") + f" {name}")
            if not ok and err:
                st.caption(err)
    st.write(("✅" if ffmpeg_in_path() else "❌") + " ffmpeg në PATH")

# ---------------- One‑Click Pipeline ----------------
st.header("⚡ One‑Click Pipeline")
st.caption("Zgjidh burimin, emrin e sesionit dhe shtyp butonin. Sistemi do transkriptojë me caching dhe do prodhojë raportet.")

session_tag = st.text_input("Emri i sesionit (do përdoret në emrat e skedarëve të output-it)", placeholder="p.sh. 2025-10-06_Batch1")

source = st.radio("Burimi i audios:", ["Lokal (folder me audio)", "Drive (Session Folder ID)"], index=0, horizontal=True)

colA, colB, colC = st.columns(3)
with colA:
    reuse_existing = st.checkbox("Shmang duplikimet (caching)", value=True)
with colB:
    save_docx = st.checkbox("Ruaj edhe .docx", value=False)
with colC:
    force = st.checkbox("Forco rinormalizim/ritranskriptim", value=False)

max_calls = st.number_input("Maksimumi i thirrjeve", 1, 10000, 500)

# Opsional: CSV mapping (filename,agent,campaign)
mapping_file = st.file_uploader("Opsional: CSV mapping (kolonat: filename, agent, campaign)", type=["csv"])

def parse_mapping_csv(buf) -> dict:
    if not buf: return {}
    text = buf.getvalue().decode("utf-8", errors="ignore")
    rdr = csv.DictReader(io.StringIO(text))
    m = {}
    for row in rdr:
        fname = (row.get("filename") or "").strip().lower()
        if not fname: continue
        m[fname] = {
            "agent": (row.get("agent") or "").strip(),
            "campaign": (row.get("campaign") or "").strip(),
        }
    return m

AUDIO_EXTS = {".mp3",".wav",".m4a",".mp4",".ogg",".flac"}
COMMON_BAD = {"new folder","documents","downloads","desktop","vicidial_agent","data","out_analysis"}

def pick_agent_from_path(p: pathlib.Path) -> str:
    parts = [x.lower() for x in p.parts]
    for seg in reversed(parts):
        s = seg.replace("_"," ").strip()
        if len(s.split()) <= 3 and s not in COMMON_BAD and "." not in s:
            return s.title()
    return "UNKNOWN"

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

if source == "Lokal (folder me audio)":
    local_audio_root = st.text_input("Path i folderit lokal me audio", value=str(pathlib.Path.cwd()))
else:
    drive_session_raw = st.text_input("Drive: Session Folder ID (ose link i plotë)")
    if st.button("Re-link Google Drive (re-auth)"):
        try:
            from core.drive_io import force_reauth
            force_reauth(readonly=True)
            st.success("Relidhja u krye.")
        except Exception as e:
            st.error(f"Re-auth dështoi: {e}")

run = st.button("Nise pipeline‑in", type="primary", use_container_width=True)

if run:
    if not session_tag:
        st.error("Vendos një emër sesioni.")
        st.stop()

    mapping = parse_mapping_csv(mapping_file) if mapping_file else {}
    prog = st.progress(0, text="Duke nisur pipeline-in...")
    status = st.empty()

    # 1) Mblidh audion
    audio_paths = []
    if source == "Lokal (folder me audio)":
        root = pathlib.Path(local_audio_root)
        audio_paths = [p for p in root.rglob("*") if p.suffix.lower() in AUDIO_EXTS]
        if not audio_paths:
            st.warning("S'u gjet asnjë audio në atë folder.")
            st.stop()
        audio_paths = audio_paths[: int(max_calls)]
        status.info(f"U gjetën {len(audio_paths)} audio lokale.")
    else:
        # Drive
        m = re.search(r"/folders/([A-Za-z0-9_-]+)", (drive_session_raw or "").strip())
        drive_session_id = m.group(1) if m else (drive_session_raw or "").strip()
        creds = get_user_oauth_creds(readonly=True)
        drive = build("drive", "v3", credentials=creds)
        items = drive_walk_audio(drive, drive_session_id)
        if not items:
            st.warning("S'u gjet asnjë audio në atë folder Drive.")
            st.stop()
        tmpdir = pathlib.Path("tmp_pipeline_audio"); tmpdir.mkdir(exist_ok=True)
        total_download = min(len(items), int(max_calls))
        for i, (fid, name, folder_path) in enumerate(items[:total_download], 1):
            outp = tmpdir / name
            drive_download_file(drive, fid, outp)
            audio_paths.append(outp)
            prog.progress(int(i/total_download*20), text=f"Shkarkim nga Drive {i}/{total_download}…")
        status.info(f"U shkarkuan {len(audio_paths)} audio nga Drive.")

    # 2) Transkripto me caching/smart-normalize
    prog.progress(25, text="Transkriptim…")
    out = transcribe_audio_files(
        input_paths=audio_paths,
        out_dir=OUT_DIR,
        mode="per-file",
        session_name=session_tag,
        subpath="Transkripte",
        save_txt=True,
        save_docx=save_docx,
        reuse_existing=reuse_existing,
        force=force,
    )

    txts = out.get("txt_paths", [])
    status.info(f"U krijuan {len(txts)} transkripte. Po përgatis analizën…")

    # 3) Ndërto metadatë për analizë
    prog.progress(60, text="Përgatitje analizash…")
    calls = []
    for p in txts:
        agent_guess = pick_agent_from_path(p)
        campaign_guess = p.parent.name if p.parent else "UNKNOWN"
        stem = p.name.lower()
        if stem in mapping:
            agent_guess = mapping[stem].get("agent") or agent_guess
            campaign_guess = mapping[stem].get("campaign") or campaign_guess
        meta = {"call_id": p.name, "agent": agent_guess, "campaign": campaign_guess,
                "start_time": datetime.now(timezone.utc).isoformat(), "duration_sec": None, "language": "auto",
                "transcript_path": str(p), "source":"local", "processed_at": datetime.now(timezone.utc).isoformat()}
        calls.append(meta)

    # 4) Analizo dhe prodho raportet
    prog.progress(85, text="Analizë LLM + Raporte…")
    call_csv, weekly_csv, xlsx = write_outputs_and_report(calls, session_tag=session_tag)

    prog.progress(100, text="✅ Përfunduar")
    status.success("Pipeline u përfundua me sukses. Shkarko output-et më poshtë.")

    col1, col2, col3 = st.columns(3)
    with open(call_csv, "rb") as f:
        col1.download_button("⬇️ call_analysis", f.read(), file_name=pathlib.Path(call_csv).name,
                             mime="text/csv", use_container_width=True)
    with open(weekly_csv, "rb") as f:
        col2.download_button("⬇️ agent_summary_weekly", f.read(), file_name=pathlib.Path(weekly_csv).name,
                             mime="text/csv", use_container_width=True)
    with open(xlsx, "rb") as f:
        col3.download_button("⬇️ Raport_Analize", f.read(), file_name=pathlib.Path(xlsx).name,
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

st.markdown("---")
st.caption("Këshillë: përdor **session_tag** unik për çdo batch që të shmangësh mbishkrimin e skedarëve.")
