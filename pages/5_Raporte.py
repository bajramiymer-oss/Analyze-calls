import streamlit as st
from core.config import CALL_CSV, AGENT_WEEKLY_CSV, EXCEL_REPORT

st.title("📊 Raporte")

st.write("Shkarko output-et e fundit të gjeneruara nga Analiza Automatike.")

col1, col2, col3 = st.columns(3)

if CALL_CSV.exists():
    with open(CALL_CSV, "rb") as f:
        col1.download_button(
            "⬇️ Shkarko call_analysis.csv",
            data=f.read(),
            file_name=CALL_CSV.name,
            mime="text/csv",
            use_container_width=True,
        )
else:
    col1.info("call_analysis.csv nuk u gjet.")

if AGENT_WEEKLY_CSV.exists():
    with open(AGENT_WEEKLY_CSV, "rb") as f:
        col2.download_button(
            "⬇️ Shkarko agent_summary_weekly.csv",
            data=f.read(),
            file_name=AGENT_WEEKLY_CSV.name,
            mime="text/csv",
            use_container_width=True,
        )
else:
    col2.info("agent_summary_weekly.csv nuk u gjet.")

if EXCEL_REPORT.exists():
    with open(EXCEL_REPORT, "rb") as f:
        col3.download_button(
            "⬇️ Shkarko Raport_Analize.xlsx",
            data=f.read(),
            file_name=EXCEL_REPORT.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
else:
    col3.info("Raport_Analize.xlsx nuk u gjet.")
