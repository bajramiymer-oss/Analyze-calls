import streamlit as st
from core.config import CALL_CSV, AGENT_WEEKLY_CSV, EXCEL_REPORT
from pathlib import Path

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

# -------------- Smart Reports Summary Section --------------
st.markdown("---")

# Check if there's a last report in session state
if "last_smart_report" in st.session_state:
    report = st.session_state["last_smart_report"]

    with st.expander("📊 Smart Report — Përmbledhje e Fundit", expanded=False):
        st.markdown(f"""
        ### 📈 Raporti i Gjeneruar: **{report['timestamp']}**

        **Kampanja:** {report['campaign']}
        **IVR Code:** {report['ivr_code']}
        **Periudha:** {report['from_date']} deri {report['to_date']}
        """)

        st.markdown("---")

        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="📞 Total Telefonata",
                value=f"{report['total_dials']:,}"
            )

        with col2:
            st.metric(
                label="📲 Inbound Calls",
                value=f"{report['inbound_calls']:,}"
            )

        with col3:
            st.metric(
                label="⏱️ Total Minuta",
                value=f"{report['total_minutes']:,.0f}"
            )

        with col4:
            st.metric(
                label="💰 Kosto VoIP",
                value=f"€ {report['voip_cost_eur']:,.2f}"
            )

        st.markdown("---")

        # Additional metrics
        col_info1, col_info2, col_info3 = st.columns(3)

        with col_info1:
            st.info(f"🎯 **Resa:** {report['resa_percent']:.2f}%")

        with col_info2:
            st.info(f"⏳ **Kohëzgjatja mesatare:** {report['avg_duration_min']:.2f} min")

        with col_info3:
            st.info(f"💵 **Kosto/thirrje:** €{report['cost_per_call_eur']:.4f}")

        st.caption("ℹ️ Ky raport gjenerohet çdo herë që ekzekuton 'Gjenero raportin' tek **Rezultatet e Listave**.")
else:
    st.info("📊 Smart Report — Nuk ka raport të gjeneruar akoma. Shko te **Rezultatet e Listave** për të gjeneruar një raport të ri.")
