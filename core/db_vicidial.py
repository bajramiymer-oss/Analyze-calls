

import os
from typing import Sequence, Dict, Any, Optional, Iterable
import pymysql
import streamlit as st

# Global variable to store current DB selection
_CURRENT_DB_KEY = "db"

def set_db_connection(db_key: str):
    """Set which database to use for queries.

    Args:
        db_key: "db" for default database, "db2" for second database
    """
    global _CURRENT_DB_KEY
    _CURRENT_DB_KEY = db_key

def get_current_db_key() -> str:
    """Get currently selected database key."""
    return _CURRENT_DB_KEY

# -------------------- Secrets / Connection --------------------
def _read_db_secrets(db_key: str = "db"):
    """Read database credentials from secrets or environment variables.

    Args:
        db_key: Key in secrets.toml (e.g., "db" or "db2")
    """
    host = user = password = database = None
    try:
        s = st.secrets.get(db_key, {})
        host = s.get("host"); user = s.get("user")
        password = s.get("password"); database = s.get("database")
    except Exception:
        pass
    # Fallback to environment variables only for default "db"
    if db_key == "db":
        host = host or os.getenv("DB_HOST")
        user = user or os.getenv("DB_USER")
        password = password or os.getenv("DB_PASSWORD")
        database = database or os.getenv("DB_NAME")
    return host, user, password, database

def get_conn(db_key: Optional[str] = None):
    """Get database connection.

    Args:
        db_key: Key in secrets.toml (e.g., "db" for default, "db2" for second database)
                If None, uses the currently selected database from _CURRENT_DB_KEY
    """
    if db_key is None:
        db_key = _CURRENT_DB_KEY
    host, user, password, database = _read_db_secrets(db_key)
    if not all([host, user, password, database]):
        raise RuntimeError(f"Kredencialet e DB '{db_key}' mungojnë. Vendosi te .streamlit/secrets.toml nën [{db_key}] host/user/password/database.")
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

# -------------------- Smart Report helpers --------------------
def fetch_outbound_by_list_statuses(from_ts: str, to_ts: str, campaign_id: str, statuses: Sequence[str] | None) -> Sequence[Dict[str, Any]]:
    """Outbound dials and total seconds for a campaign in time window, filtered by statuses.

    Time window uses [from_ts, to_ts) semantics.
    """
    # Build optional status filter
    where_status = ""
    params: list = [from_ts, to_ts, campaign_id]
    if statuses and len(list(statuses)) > 0:
        placeholders = ",".join(["%s"] * len(statuses))
        where_status = f" AND vl.status IN ({placeholders})"
        params.extend(list(statuses))

    sql = f'''
        SELECT vl.list_id,
               COALESCE(vls.list_name, CONCAT('LIST ', vl.list_id)) AS list_name,
               COUNT(*) AS total_dials,
               COALESCE(SUM(vl.length_in_sec), 0) AS total_sec
        FROM vicidial_log vl
        LEFT JOIN vicidial_lists vls ON vls.list_id = vl.list_id
        WHERE vl.call_date >= %s AND vl.call_date < %s
          AND vl.campaign_id = %s
          {where_status}
        GROUP BY vl.list_id, vls.list_name
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_inbound_calls_by_list(from_ts: str, to_ts: str, campaign_id: str, ivr_code: str) -> Dict[int, int]:
    """Return mapping {list_id -> inbound_calls} using existing IVR logic."""
    rows = fetch_inbound_by_list(from_ts, to_ts, campaign_id, ivr_code)
    out: Dict[int, int] = {}
    for r in rows or []:
        try:
            out[int(r["list_id"])] = int(r["inbound_calls"])
        except Exception:
            # Be tolerant to DB type coercions
            out[int(r.get("list_id"))] = int(r.get("inbound_calls", 0))
    return out


def fetch_list_names(list_ids: Iterable[int]) -> Sequence[Dict[str, Any]]:
    """Fetch list_id -> list_name for provided IDs."""
    ids = list({int(x) for x in list_ids if x is not None})
    if not ids:
        return []
    placeholders = ",".join(["%s"] * len(ids))
    sql = f"""
        SELECT list_id, list_name
        FROM vicidial_lists
        WHERE list_id IN ({placeholders})
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, ids)
        return cur.fetchall()


def fetch_status_distribution_by_list(from_ts: str, to_ts: str, campaign_id: str) -> Sequence[Dict[str, Any]]:
    """Return rows grouped by list_id and status with counts and total_sec."""
    sql = '''
        SELECT vl.list_id,
               vl.status,
               COUNT(*) AS calls,
               COALESCE(SUM(vl.length_in_sec), 0) AS total_sec
        FROM vicidial_log vl
        WHERE vl.call_date >= %s AND vl.call_date < %s
          AND vl.campaign_id = %s
        GROUP BY vl.list_id, vl.status
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (from_ts, to_ts, campaign_id))
        return cur.fetchall()


def fetch_time_buckets_by_list(from_ts: str, to_ts: str, campaign_id: str) -> Sequence[Dict[str, Any]]:
    """Return rows grouped by list_id, hour_bucket (00-23), weekday (1-7) with dials and total_sec."""
    sql = '''
        SELECT vl.list_id,
               DATE_FORMAT(vl.call_date, '%%H') AS hour_bucket,
               DAYOFWEEK(vl.call_date) AS weekday,
               COUNT(*) AS dials,
               COALESCE(SUM(vl.length_in_sec), 0) AS total_sec
        FROM vicidial_log vl
        WHERE vl.call_date >= %s AND vl.call_date < %s
          AND vl.campaign_id = %s
        GROUP BY vl.list_id, hour_bucket, weekday
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (from_ts, to_ts, campaign_id))
        return cur.fetchall()


def fetch_inbound_buckets_by_list(
    from_ts: str,
    to_ts: str,
    campaign_id: str,
    ivr_code: str,
) -> Sequence[Dict[str, Any]]:
    """Inbound grouped by list_id, hour (00-23), weekday (1-7) using IVR responses.

    Join vir.lead_id → vicidial_list → list_id to attribute to lists.
    """
    sql = '''
        SELECT vls.list_id AS list_id,
               DATE_FORMAT(vir.created, '%%H') AS hour_bucket,
               DAYOFWEEK(vir.created) AS weekday,
               COUNT(*) AS inbound_calls
        FROM vicidial_ivr_response vir
        INNER JOIN vicidial_list vl ON vir.lead_id = vl.lead_id
        INNER JOIN vicidial_lists vls ON vls.list_id = vl.list_id
        WHERE vir.campaign = %s
          AND vir.created >= %s AND vir.created < %s
          AND vir.response = %s
        GROUP BY vls.list_id, hour_bucket, weekday
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (campaign_id, from_ts, to_ts, ivr_code))
        return cur.fetchall()


# -------------------- Phone-level aggregations --------------------
def fetch_dials_by_phone(from_ts: str, to_ts: str, campaign_id: str, statuses: Sequence[str] | None) -> Sequence[Dict[str, Any]]:
    """Return dials and total_sec grouped by phone_number.

    If statuses is None → ALL statuses; else filter with IN (...).
    """
    where_status = ""
    params: list = [from_ts, to_ts, campaign_id]
    if statuses and len(list(statuses)) > 0:
        placeholders = ",".join(["%s"] * len(statuses))
        where_status = f" AND vl.status IN ({placeholders})"
        params.extend(list(statuses))
    sql = f'''
        SELECT vl.phone_number,
               COUNT(*) AS dials,
               COALESCE(SUM(vl.length_in_sec), 0) AS total_sec,
               vli.province
        FROM vicidial_log vl
        LEFT JOIN vicidial_list vli ON vl.lead_id = vli.lead_id
        WHERE vl.call_date >= %s AND vl.call_date < %s
          AND vl.campaign_id = %s
          {where_status}
        GROUP BY vl.phone_number, vli.province
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_inbound_by_phone(from_ts: str, to_ts: str, campaign_id: str, ivr_code: str) -> Sequence[Dict[str, Any]]:
    """Return inbound counts grouped by phone_number using IVR responses."""
    sql = '''
        SELECT vl.phone_number,
               COUNT(*) AS inbound_calls,
               vli.province
        FROM vicidial_ivr_response vir
        INNER JOIN vicidial_list vl ON vir.lead_id = vl.lead_id
        LEFT JOIN vicidial_list vli ON vl.lead_id = vli.lead_id
        WHERE vir.campaign = %s
          AND vir.created >= %s AND vir.created < %s
          AND vir.response = %s
        GROUP BY vl.phone_number, vli.province
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (campaign_id, from_ts, to_ts, ivr_code))
        return cur.fetchall()


# -------------------- SVYCLM quality --------------------
def fetch_svyclm_by_list(from_ts: str, to_ts: str, campaign_id: str) -> Sequence[Dict[str, Any]]:
    sql = '''
        SELECT vl.list_id,
               COUNT(*) AS svyclm_calls,
               COALESCE(SUM(vl.length_in_sec), 0) AS svyclm_sec
        FROM vicidial_log vl
        WHERE vl.call_date >= %s AND vl.call_date < %s
          AND vl.campaign_id = %s
          AND vl.status = 'SVYCLM'
        GROUP BY vl.list_id
    '''
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (from_ts, to_ts, campaign_id))
        return cur.fetchall()


def fetch_svyclm_timeout_by_list(from_ts: str, to_ts: str, campaign_id: str, timeout_codes: Sequence[str]) -> Sequence[Dict[str, Any]]:
    """Count timeouts based on IVR response codes (e.g., TIMEOUT) grouped by list via lead mapping."""
    placeholders = ",".join(["%s"] * len(timeout_codes)) if timeout_codes else "%s"
    sql = f'''
        SELECT vls.list_id AS list_id,
               COUNT(*) AS svyclm_timeout
        FROM vicidial_ivr_response vir
        INNER JOIN vicidial_list vl ON vir.lead_id = vl.lead_id
        INNER JOIN vicidial_lists vls ON vl.list_id = vls.list_id
        WHERE vir.campaign = %s
          AND vir.created >= %s AND vir.created < %s
          AND vir.response IN ({placeholders})
        GROUP BY vls.list_id
    '''
    params = [campaign_id, from_ts, to_ts] + (list(timeout_codes) if timeout_codes else ["TIMEOUT"])
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
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
