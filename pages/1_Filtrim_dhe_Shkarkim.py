
import pathlib
from datetime import datetime, time
import streamlit as st
from core.db_vicidial import list_recordings
from core.downloader_vicidial import download_recording
from core.config import OUT_DIR
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.title("📥 Filtrim & Shkarkim (Vicidial DB → Lokale)")
st.caption("Merr regjistrimet nga `recording_log` dhe i ruan lokalisht gati për ’Drive Upload’.")

# Lexo filtrat globalë nga Home si defaults
gf = st.session_state.get("global_filters", {})
start_date = st.date_input("Data fillimit", value=gf.get("start_date"))
start_time = st.time_input("Ora fillimit", value=gf.get("start_time", time(0,0,0)))
end_date = st.date_input("Data mbarimit", value=gf.get("end_date"))
end_time = st.time_input("Ora mbarimit", value=gf.get("end_time", time(23,59,59)))
session_name = st.text_input("Emri i Session-it", value=gf.get("session_name",""))
campaign = st.text_input("Fushata (Campaign)", value=gf.get("campaign",""), help="Filtron join-in me vicidial_log (opsionale)")
max_files = st.number_input("Maksimumi i skedarëve për shkarkim", 1, 100000, 500)

# Basic auth për serverin e recordings (nëse duhet)
colA, colB = st.columns(2)
with colA:
    basic_user = st.text_input("Basic auth user (nëse duhet)")
with colB:
    basic_pass = st.text_input("Basic auth pass (nëse duhet)", type="password")

run = st.button("⬇️ Shkarko regjistrimet", type="primary", disabled=not session_name)

if run:
    start_dt = datetime.combine(start_date, start_time).strftime("%Y-%m-%d %H:%M:%S")
    end_dt = datetime.combine(end_date, end_time).strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"Po kërkoj regjistrimet nga DB: {start_dt} → {end_dt} | campaign={campaign or '(të gjitha)'}")

    try:
        rows = list_recordings(start_dt, end_dt, campaign.strip() or None, limit=int(max_files))
    except Exception as e:
        st.error(f"Gabim gjatë query: {e}")
        st.stop()

    if not rows:
        st.warning("S'u gjet asnjë regjistrim në këtë interval/filtra.")
        st.stop()

    # Strukturë lokale: out_analysis/<Session>/<Campaign>/<Agent>/file
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    root = OUT_DIR / session_name
    downloaded = 0
    failed = 0

    prog = st.progress(0, text="Duke shkarkuar...")
    total = len(rows)
    for i, r in enumerate(rows, start=1):
        user = (r.get("user") or "UNKNOWN").strip().title()
        campaign_id = (r.get("campaign_id") or (campaign or "UNKNOWN")).strip()
        filename = r.get("filename") or "recording"
        location = r.get("location") or ""
        ext = pathlib.Path(location).suffix or ".wav"
        safe_user = user.replace("/", "-")
        safe_campaign = campaign_id.replace("/", "-")

        out_dir = root / safe_campaign / safe_user
        out_file = out_dir / f"{filename}{ext}"
        try:
            ok = download_recording(location, out_file, auth=(basic_user, basic_pass) if basic_user or basic_pass else None)
            if ok:
                downloaded += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            st.write(f"🚫 {filename}: {e}")

        prog.progress(int(i/total*100), text=f"Shkarkim: {i}/{total} • {int(i/total*100)}%")

        if downloaded >= max_files:
            break

    st.success(f"Shkarkim i përfunduar. ✅ Sukses: {downloaded} • ❌ Dështime: {failed}")
    st.info(f"Skedarët janë ruajtur te: `{root}`. Pastaj hap ’Drive Upload’ për t'i dërguar në Drive.")

from core.config import list_vicidial_sources, get_vicidial_db_conf
sources = list_vicidial_sources()
src_names = list(sources.keys()) or ["default"]
pick = st.selectbox("Zgjidh Vicidial DB", src_names, index=0)

conf = get_vicidial_db_conf(pick)
if not conf:
    st.error("Nuk u gjet konfigurimi për këtë burim.")
    st.stop()

# kur krijon lidhjen DB, përdor conf:
# pymysql.connect(host=conf["host"], user=conf["user"], password=conf["password"], database=conf["database"], ...)
