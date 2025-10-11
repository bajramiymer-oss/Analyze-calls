import mimetypes
import pathlib
from collections import defaultdict
from typing import Dict, List
import streamlit as st
from googleapiclient.discovery import build
from core.drive_io import get_user_oauth_creds, ensure_path, upload_file, force_reauth

st.title("☁️ Drive Upload")
st.caption("Struktura: <Parent>/<Session>/<Kampanja>/<Agjent>/…")

# Parent ID
PARENT_ID = None
try:
    PARENT_ID = st.secrets.get("drive", {}).get("parent_id")
except Exception:
    pass
if not PARENT_ID:
    try:
        from core.config import DRIVE_PARENT_ID as _PID
        PARENT_ID = _PID
    except Exception:
        PARENT_ID = ""

colA, colB = st.columns(2)
with colA:
    local_root = st.text_input("Folder lokal me regjistrime (audio)", value=str(pathlib.Path.cwd()))
with colB:
    parent_id = st.text_input("Parent Folder ID në Drive", value=PARENT_ID or "", help="ID e folderit ku do krijohet Session/Campaign/Agent")

session_name = st.text_input("Emri i Folderit kryesor (Session)", placeholder="p.sh. 2025-10-06_Batch1")
campaign_name = st.text_input("Emri i fushatës (Campaign)", placeholder="p.sh. AUTOBIZ")

col1, col2 = st.columns(2)
with col1:
    run = st.button("Ngarko në Drive", type="primary", disabled=not (local_root and parent_id and session_name and campaign_name))
with col2:
    if st.button("Re-link Google Drive (re-auth)"):
        try:
            force_reauth(readonly=False)
            st.success("Relidhja u krye. Mund të vazhdosh me ngarkimet.")
        except Exception as e:
            st.error(f"Re-auth dështoi: {e}")

BAD = {"new folder","downloads","desktop","vicidial_agent","data","out_analysis","audio","records","regjistrime"}

def guess_agent_from_path(p: pathlib.Path) -> str:
    for seg in reversed(p.parts):
        s = seg.replace("_"," ").strip()
        if "." in s:
            continue
        words = s.split()
        if 1 <= len(words) <= 3 and s.lower() not in BAD:
            return s.title()
    return "UNKNOWN"

if run:
    root = pathlib.Path(local_root)
    if not root.exists():
        st.error("Folderi lokal nuk ekziston.")
        st.stop()

    audio_exts = {".mp3",".wav",".m4a",".mp4",".ogg",".flac",".txt",".docx"}
    files = [p for p in root.rglob("*") if p.suffix.lower() in audio_exts]
    if not files:
        st.warning("S'u gjet asnjë file audio/transkriptim në atë folder.")
        st.stop()

    creds = get_user_oauth_creds(readonly=False)
    drive = build("drive", "v3", credentials=creds)

    session_id = ensure_path(drive, parent_id, [session_name])
    campaign_id = ensure_path(drive, session_id, [campaign_name])

    grouped: Dict[str, List[pathlib.Path]] = defaultdict(list)
    for p in files:
        agent = guess_agent_from_path(p)
        grouped[agent].append(p)

    total = sum(len(v) for v in grouped.values())
    prog = st.progress(0, text="Duke ngarkuar...")
    done = 0

    for agent, plist in grouped.items():
        agent_folder_id = ensure_path(drive, campaign_id, [agent])
        for p in plist:
            mime, _ = mimetypes.guess_type(str(p))
            try:
                upload_file(drive, agent_folder_id, str(p), mime_type=mime)
                done += 1
                percent = int(done/total*100)
                prog.progress(percent, text=f"Ngarkim: {done}/{total} • {percent}%")
            except Exception as e:
                st.write(f"🚫 {p.name}: {e}")

    st.success(f"U ngarkuan {done}/{total} file në Drive te {session_name}/{campaign_name}/<Agent>/")
    st.info("Tani vazhdo te ’Analizë Automatike’ me 'Nga Drive (Session ID)'.")
