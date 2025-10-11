
import io
from datetime import datetime, time
from pathlib import Path
import pandas as pd
import streamlit as st
from core.db_vicidial import fetch_outbound_by_list, fetch_inbound_by_list
from core.config import OUT_DIR

st.title("📈 Rezultatet e listave")
st.caption("Llogarit performancën e listave (OUTBOUND me statuset PU/SVYCLM) dhe INBOUND sipas IVR për një kampanjë të zgjedhur.")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data fillimit")
    start_time = st.time_input("Ora fillimit", value=time(0,0,0))
with col2:
    end_date = st.date_input("Data mbarimit")
    end_time = st.time_input("Ora mbarimit", value=time(23,59,59))

campaign = st.text_input("Kampanja (p.sh. AUTOBIZ)", placeholder="Emri i kampanjës")
ivr_code = st.text_input("IVR code (p.sh. 1)", placeholder="vlera e butonit p.sh. 1")

run = st.button("Gjenero raportin", type="primary", disabled=not (campaign and ivr_code))

if run:
    start_dt = datetime.combine(start_date, start_time).strftime("%Y-%m-%d %H:%M:%S")
    end_dt = datetime.combine(end_date, end_time).strftime("%Y-%m-%d %H:%M:%S")

    prog = st.progress(0, text="Duke lexuar OUTBOUND...")
    try:
        outbound_rows = fetch_outbound_by_list(start_dt, end_dt)
        prog.progress(30, text="Duke lexuar INBOUND...")
        inbound_rows = fetch_inbound_by_list(start_dt, end_dt, campaign.strip(), ivr_code.strip())
    except Exception as e:
        st.error(f"Gabim gjatë leximit të DB: {e}")
        st.stop()

    df_out = pd.DataFrame(outbound_rows) if outbound_rows else pd.DataFrame(columns=["list_id","list_name","outbound_calls"])
    df_in = pd.DataFrame(inbound_rows) if inbound_rows else pd.DataFrame(columns=["list_id","inbound_calls"])

    df = pd.merge(df_out, df_in, on="list_id", how="left")
    df["inbound_calls"] = df["inbound_calls"].fillna(0).astype(int)
    df["outbound_calls"] = df["outbound_calls"].fillna(0).astype(int)

    def calc_resa(row):
        ob = row["outbound_calls"]
        ib = row["inbound_calls"]
        if ob <= 0:
            return 0.0
        return round((ib / ob) * 1000.0, 3)

    df["RESA"] = df.apply(calc_resa, axis=1)

    df = df.rename(columns={
        "list_id": "ID",
        "list_name": "PROVINCIA",
        "outbound_calls": "OUTBOUND",
        "inbound_calls": "INBOUND"
    })

    df = df.sort_values(by="RESA", ascending=False).reset_index(drop=True)

    prog.progress(70, text="Duke gjeneruar Excel...")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    start_tag = datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d-%H%M")
    end_tag = datetime.strptime(end_dt, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d-%H%M")
    file_name = f"Liste_{start_tag}_to_{end_tag}_IVR-{ivr_code.strip()}.xlsx"
    out_path = OUT_DIR / file_name

    with pd.ExcelWriter(out_path.as_posix(), engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Rezultatet", index=False)

    prog.progress(100, text="✅ U krijua Excel-i i rezultateve")

    st.success("Raporti u krijua me sukses.")
    st.dataframe(df, use_container_width=True)

    with open(out_path, "rb") as f:
        st.download_button(
            "⬇️ Shkarko Excel-in e listave",
            data=f.read(),
            file_name=out_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
