"""
app.py - Dashboard Kryesor
Version: v2.0 - Overview & Quick Access
Author: Protrade AI
"""

import streamlit as st
import pathlib
from datetime import datetime

st.set_page_config(
    page_title="Dashboard - Vicidial Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== HEADER ==============
st.title("📊 Dashboard - Pasqyrë e Përgjithshme")
st.markdown("### Vicidial Call Analysis Platform")

st.markdown("""
---
## 🚀 Çfarë mund të bësh këtu?

Ky është një sistem i plotë për analizën e telefonatave nga Vicidial që kombinon:
- 📥 Shkarkim automatik nga databaza
- 📝 Transkriptim me AI (OpenAI Whisper)
- 🤖 Analizë e avancuar me GPT-4
- 📊 Gjenerim raportesh në Excel
- 🎯 Kontekste të personalizuara për fushata të ndryshme
""")

# ============== PACKAGE CHECKS ==============
def check_pkg(name):
    try:
        __import__(name)
        return True, ""
    except Exception as e:
        return False, str(e)

checks = {}
required_pkgs = ["openpyxl", "pymysql", "requests", "googleapiclient", "google_auth_oauthlib", "openai"]
optional_pkgs = ["PyPDF2", "docx", "librosa"]

for pkg in required_pkgs:
    ok, err = check_pkg(pkg if pkg != "docx" else "docx")
    checks[pkg] = (ok, err, True)  # True = required

for pkg in optional_pkgs:
    ok, err = check_pkg(pkg if pkg != "docx" else "docx")
    checks[pkg] = (ok, err, False)  # False = optional

with st.expander("🩺 Statusi i Sistemit", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Paketa të Nevojshme")
        for name, (ok, err, required) in checks.items():
            if required:
                icon = "✅" if ok else "❌"
                st.write(f"{icon} {name}")
                if not ok and err:
                    st.caption(f"⚠️ {err[:80]}")

    with col2:
        st.markdown("#### Paketa Opsionale")
        for name, (ok, err, required) in checks.items():
            if not required:
                icon = "✅" if ok else "⚪"
                st.write(f"{icon} {name}")

        # OpenAI Key check
        import os
        has_key = bool(os.getenv("OPENAI_API_KEY"))
        if not has_key:
            try:
                has_key = bool(st.secrets.get("OPENAI_API_KEY"))
            except:
                pass
        st.write(("✅" if has_key else "❌") + " OPENAI_API_KEY")

st.markdown("---")

# ============== QUICK ACCESS MENU ==============
st.markdown("## 🎯 Zgjidhni ku të shkoni:")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### ⚡ Pipeline Komplet")
    st.markdown("""
    **Procesi i plotë automatik:**
    - 📞 Vicidial Database
    - 📁 Folder Lokal
    - ☁️ Google Drive

    → Transkriptim → Analizë → Raport

    🎯 Mbështet kontekste fushatash
    """)
    if st.button("➡️ Shko te Pipeline Komplet", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Pipeline_Komplet.py")

with col2:
    st.markdown("### 🛠️ Mjete të Ndara")
    st.markdown("""
    **Ekzekuto hapa individualë:**
    - 📥 Filtrim & Shkarkim
    - ☁️ Drive Upload
    - 📝 Transkriptim Manual

    Për testing dhe debugging
    """)
    if st.button("➡️ Shko te Mjete", use_container_width=True):
        st.switch_page("pages/4_Tools.py")

with col3:
    st.markdown("### 📊 Raporte & Settings")
    st.markdown("""
    **Raportet dhe konfigurimet:**
    - 📈 Smart Reports
    - 📋 Rezultatet e Listave
    - ⚙️ Settings & Campaigns

    Shiko rezultatet dhe ndrysho parametrat
    """)
    if st.button("➡️ Shko te Raporte", use_container_width=True):
        st.switch_page("pages/2_Raporte.py")

st.markdown("---")

# ============== RECENT OUTPUTS ==============
st.markdown("## 📂 Outpute të Fundit")

from core.config import OUT_DIR

if OUT_DIR.exists():
    # Gjej 5 sessionet më të fundit
    sessions = []
    for item in OUT_DIR.iterdir():
        if item.is_dir():
            try:
                mtime = item.stat().st_mtime
                sessions.append((item.name, datetime.fromtimestamp(mtime), item))
            except:
                pass

    sessions.sort(key=lambda x: x[1], reverse=True)

    if sessions:
        st.markdown("### 📁 Sessionet e Fundit:")
        for i, (name, mtime, path) in enumerate(sessions[:5], 1):
            col_a, col_b, col_c = st.columns([3, 2, 1])
            with col_a:
                st.text(f"{i}. {name}")
            with col_b:
                st.caption(mtime.strftime("%Y-%m-%d %H:%M"))
            with col_c:
                # Check for Excel report
                xlsx_files = list(path.glob("Raport_Analize*.xlsx"))
                if xlsx_files:
                    with open(xlsx_files[0], "rb") as f:
                        st.download_button(
                            "⬇️ Excel",
                            f.read(),
                            file_name=xlsx_files[0].name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_{i}"
                        )
    else:
        st.info("Nuk ka outpute ende. Shko te 'Pipeline Komplet' për të filluar!")
else:
    st.info("Nuk ka outpute ende. Shko te 'Pipeline Komplet' për të filluar!")

st.markdown("---")

# ============== CAMPAIGN OVERVIEW ==============
st.markdown("## 🎯 Kampanjat e Konfiguruara")

from core.campaign_manager import get_all_campaigns

campaigns = get_all_campaigns()

if campaigns:
    st.markdown(f"**Total:** {len(campaigns)} fushatë/kontekste")

    # Show first 3 campaigns
    for camp in campaigns[:3]:
        with st.expander(f"📁 {camp['name']}", expanded=False):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.caption(f"**Dokumente:** {len(camp.get('documents', []))}")
                st.caption(f"**Faqe totale:** {camp.get('total_pages', 0)}")
            with col_c2:
                st.caption(f"**Krijuar:** {camp['created_date'][:10]}")
                st.caption(f"**Modifikuar:** {camp['last_modified'][:10]}")

            if camp.get('project_context_hint'):
                st.text_area("Konteksti:", value=camp['project_context_hint'][:150] + "...", height=60, disabled=True, key=f"camp_ctx_{camp['id']}")

    if len(campaigns) > 3:
        st.caption(f"+ {len(campaigns) - 3} të tjera...")

    if st.button("➡️ Menaxho Kampanjat", use_container_width=True):
        st.switch_page("pages/5_Settings.py")
else:
    st.info("Nuk ka kampanja të konfiguruara. Shko te 'Settings' për të krijuar!")
    if st.button("➡️ Krijo Kampanjën e Parë", use_container_width=True):
        st.switch_page("pages/5_Settings.py")

st.markdown("---")

# ============== QUICK STATS ==============
st.markdown("## 📈 Statistika të Shpejta")

col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

# Count total transcripts
total_transcripts = 0
total_analyses = 0
total_size_mb = 0

if OUT_DIR.exists():
    for session_dir in OUT_DIR.iterdir():
        if session_dir.is_dir():
            # Count transcripts
            transcript_dir = session_dir / "Transkripte"
            if transcript_dir.exists():
                total_transcripts += len(list(transcript_dir.rglob("*.txt")))

            # Count analyses
            csv_files = list(session_dir.glob("call_analysis*.csv"))
            if csv_files:
                total_analyses += 1

            # Calculate size
            try:
                for f in session_dir.rglob("*"):
                    if f.is_file():
                        total_size_mb += f.stat().st_size / (1024 * 1024)
            except:
                pass

with col_stat1:
    st.metric("Transkripte", f"{total_transcripts}")

with col_stat2:
    st.metric("Analiza", f"{total_analyses}")

with col_stat3:
    st.metric("Kampanja", f"{len(campaigns)}")

with col_stat4:
    st.metric("Hapësira", f"{total_size_mb:.1f} MB")

st.markdown("---")

# ============== FOOTER ==============
st.info("""
💡 **Këshillë për fillim:**
1. Shko te **Settings** dhe krijo një kampanjë të re me kontekst dhe dokumente
2. Shko te **Pipeline Komplet** dhe zgjidh kampanjën që krijove
3. Ngarko audio ose lidhu me Vicidial/Drive dhe kliko "Nise Pipeline-in"
4. Prit rezultatet dhe shiko raportet në Excel! 🎉

📖 **Dokumentacion:** Çdo faqe ka instruksione të detajuara.
""")

st.caption("Protrade AI © 2025 - Vicidial Call Analysis Platform v2.0")
