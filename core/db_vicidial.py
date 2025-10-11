

import os
from typing import Sequence, Dict, Any, Optional
import pymysql
import streamlit as st

# -------------------- Secrets / Connection --------------------
def _read_db_secrets():
    host = user = password = database = None
    try:
        s = st.secrets.get("db", {})
        host = s.get("host"); user = s.get("user")
        password = s.get("password"); database = s.get("database")
    except Exception:
        pass
    host = host or os.getenv("DB_HOST")
    user = user or os.getenv("DB_USER")
    password = password or os.getenv("DB_PASSWORD")
    database = database or os.getenv("DB_NAME")
    return host, user, password, database

def get_conn():
    host, user, password, database = _read_db_secrets()
    if not all([host, user, password, database]):
        raise RuntimeError("Kredencialet e DB mungojnë. Vendosi te .streamlit/secrets.toml nën [db] host/user/password/database.")
    return pymysql.connect(host=host, user=user, password=password, database=database,
                           autocommit=True, charset="utf8mb4",
                           cursorclass=pymysql.cursors.DictCursor)

# -------------------- OUTBOUND / INBOUND për 'Rezultatet e listave' --------------------
def fetch_outbound_by_list(start_dt: str, end_dt: str) -> Sequence[Dict[str, Any]]:
    """OUTBOUND: vetëm statuset ('PU','SVYCLM') në vicidial_log brenda intervalit."""
    sql = '''
        SELECT vl.list_id,
               COALESCE(vls.list_name, CONCAT('LIST ', vl.list_id)) AS list_name,
               COUNT(*) AS outbound_calls
        FROM vicidial_log vl
        LEFT JOIN vicidial_lists vls ON vls.list_id = vl.list_id
        WHERE vl.call_date >= %s AND vl.call_date <= %s
          AND vl.status IN ('PU','SVYCLM')
        GROUP BY vl.list_id, vls.list_name
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (start_dt, end_dt))
        return cur.fetchall()

def fetch_inbound_by_list(start_dt: str, end_dt: str, campaign: str, ivr_code: str) -> Sequence[Dict[str, Any]]:
    """INBOUND: numërim per list_id për një campaign dhe një response të IVR."""
    sql = '''
        SELECT vls.list_id AS list_id,
               COUNT(*) AS inbound_calls
        FROM vicidial_ivr_response vir
        INNER JOIN vicidial_list vl ON vir.lead_id = vl.lead_id
        INNER JOIN vicidial_lists vls ON vls.list_id = vl.list_id
        WHERE vir.campaign = %s
          AND vir.created >= %s AND vir.created <= %s
          AND vir.response = %s
        GROUP BY vls.list_id
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (campaign, start_dt, end_dt, ivr_code))
        return cur.fetchall()

# -------------------- Listimi i regjistrimeve për shkarkim --------------------
def list_recordings(start_dt: str, end_dt: str, campaign: Optional[str] = None, limit: int = 10000) -> Sequence[Dict[str, Any]]:
    """Lexo regjistrimet nga recording_log brenda intervalit.
    Kthen: start_time, location, filename, lead_id, length_in_sec, user (agent), campaign_id (nëse gjendet)
    Bashkohet me vicidial_log (sipas lead_id dhe një dritare kohore rreth start_time) për të marrë user/campaign.
    """
    sql = f"""
        SELECT rl.start_time,
               rl.location,
               rl.filename,
               rl.lead_id,
               rl.length_in_sec,
               vl.user,
               vl.campaign_id
        FROM recording_log rl
        LEFT JOIN vicidial_log vl ON vl.lead_id = rl.lead_id
           AND vl.call_date BETWEEN DATE_SUB(rl.start_time, INTERVAL 1 HOUR) AND DATE_ADD(rl.start_time, INTERVAL 1 HOUR)
        WHERE rl.start_time >= %s AND rl.start_time <= %s
        { 'AND vl.campaign_id = %s' if campaign else '' }
        ORDER BY rl.start_time ASC
        LIMIT %s
    """
    params = [start_dt, end_dt]
    if campaign:
        params.append(campaign)
    params.append(limit)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()
