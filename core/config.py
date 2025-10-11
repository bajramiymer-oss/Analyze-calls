
import os, pathlib
import streamlit as st

# Rrugë output-esh
ROOT = pathlib.Path.cwd()
OUT_DIR = ROOT / "out_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CALL_CSV = OUT_DIR / "call_analysis.csv"
AGENT_WEEKLY_CSV = OUT_DIR / "agent_summary_weekly.csv"
EXCEL_REPORT = OUT_DIR / "Raport_Analize.xlsx"

# Google Drive
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/drive.file"]
DRIVE_PARENT_ID = st.secrets.get("DRIVE_PARENT_ID", "") if hasattr(st, "secrets") else ""

# Vicidial / Web
VICIDIAL_WEB = os.environ.get("VICIDIAL_WEB", "")  # p.sh. https://user:pass@vicidial.example.com

def load_openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib
        for p in [pathlib.Path.cwd()/".streamlit"/"secrets.toml", pathlib.Path.home()/".streamlit"/"secrets.toml"]:
            if p.exists():
                with open(p, "rb") as f:
                    data = tomllib.load(f)
                    if data.get("OPENAI_API_KEY"): return data["OPENAI_API_KEY"]
    except Exception:
        pass
    return ""

# --- MULTI-DB VICIDIAL ---
def list_vicidial_sources():
    """
    Kthen dict {name: {host,database,user,password}} nga secrets.[dbs].*
    Përkompatibilitet: nëse mungon 'dbs', përfshin edhe 'db' si 'default'.
    """
    try:
        import streamlit as st
        out = {}
        dbs = st.secrets.get("dbs", {})
        for name, conf in dbs.items():
            out[name] = {
                "host": conf.get("host"),
                "database": conf.get("database"),
                "user": conf.get("user"),
                "password": conf.get("password"),
            }
        if not out and "db" in st.secrets:
            d = st.secrets["db"]
            out["default"] = {
                "host": d.get("host"),
                "database": d.get("database"),
                "user": d.get("user"),
                "password": d.get("password"),
            }
        return out
    except Exception:
        return {}

def get_vicidial_db_conf(name: str):
    sources = list_vicidial_sources()
    return sources.get(name)
