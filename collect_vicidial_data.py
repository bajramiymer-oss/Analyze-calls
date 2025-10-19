"""
collect_vicidial_data.py

Script për të mbledhur të dhëna nga Vicidial për Analyzer + Recommender.
Përdor lidhjen ekzistuese të databazës nga core/db_vicidial.py

Usage:
    python collect_vicidial_data.py

Output:
    vicidial_analysis_data.json (të gjitha të dhënat)
"""

import json
from datetime import datetime, timedelta
import pymysql
import pathlib
import argparse

# Defaults (overridable via CLI)
CAMPAIGN_ID = "autobiz"
DB_KEY = "db2"
DAYS_BACK = 7  # Last N days for analysis

def _parse_args():
    parser = argparse.ArgumentParser(description="Collect Vicidial data for Analyzer")
    parser.add_argument("--campaign", dest="campaign", default=CAMPAIGN_ID)
    parser.add_argument("--db-key", dest="db_key", default=DB_KEY)
    parser.add_argument("--days", dest="days", type=int, default=DAYS_BACK)
    return parser.parse_args()

def read_secrets():
    """Lexon secrets.toml file"""
    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib
        except:
            raise RuntimeError("Instalo tomli: pip install tomli")

    secrets_path = pathlib.Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        raise RuntimeError(f"Nuk u gjet {secrets_path}")

    with open(secrets_path, "rb") as f:
        return tomllib.load(f)

def get_db_connection():
    """Krijon lidhjen me databazën"""
    secrets = read_secrets()

    # Try to get db2 config
    db_conf = secrets.get(DB_KEY, {})

    if not db_conf:
        raise RuntimeError(f"Nuk u gjet konfigurimi për [{DB_KEY}] në secrets.toml")

    host = db_conf.get("host")
    user = db_conf.get("user")
    password = db_conf.get("password")
    database = db_conf.get("database", "asterisk")

    if not all([host, user, password]):
        raise RuntimeError(f"Kredencialet janë të pakompl eta për {DB_KEY}: host={host}, user={user}")

    print(f"   Connecting to: {host}")
    print(f"   Database: {database}")
    print(f"   User: {user}")

    conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn

def execute_query(conn, query, description=""):
    """Ekzekuton një query dhe kthen rezultatet"""
    print(f"\n{'='*60}")
    print(f"Executing: {description}")
    print(f"{'='*60}")

    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            print(f"✅ Retrieved {len(results)} rows")
            return results
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def main():
    # Allow overrides via CLI
    global CAMPAIGN_ID, DB_KEY, DAYS_BACK
    try:
        args = _parse_args()
        CAMPAIGN_ID = args.campaign
        DB_KEY = args.db_key
        DAYS_BACK = int(args.days)
    except Exception:
        pass
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║     VICIDIAL DATA COLLECTION FOR AI ANALYZER              ║
║     Campaign: {CAMPAIGN_ID}                                     ║
║     Database key: {DB_KEY}                                       ║
║     Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                          ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # Connect to database
    print("\n🔌 Connecting to Vicidial database...")
    try:
        conn = get_db_connection()
        print("✅ Connected successfully!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # Data collection object
    data = {
        "collection_date": datetime.now().isoformat(),
        "campaign_id": CAMPAIGN_ID,
        "db_key": DB_KEY,
        "analysis_period_days": DAYS_BACK
    }

    # ========================================================
    # 1. CAMPAIGN CONFIGURATION
    # ========================================================
    query = f"""
    SELECT *
    FROM vicidial_campaigns
    WHERE campaign_id = '{CAMPAIGN_ID}'
    """
    results = execute_query(conn, query, "1. Campaign Configuration")
    data["campaign_config"] = results[0] if results else {}

    # ========================================================
    # 2. CUSTOM FIELDS STRUCTURE
    # ========================================================
    query = """
    SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'asterisk'
    AND TABLE_NAME = 'vicidial_list'
    AND (COLUMN_NAME LIKE '%custom%'
         OR COLUMN_NAME LIKE '%province%'
         OR COLUMN_NAME LIKE '%vendor%'
         OR COLUMN_NAME LIKE '%source%'
         OR COLUMN_NAME LIKE '%rank%'
         OR COLUMN_NAME LIKE '%quality%')
    ORDER BY ORDINAL_POSITION
    """
    results = execute_query(conn, query, "2. Custom Fields in vicidial_list")
    data["custom_fields"] = results

    # ========================================================
    # 3. ACTIVE LISTS SUMMARY
    # ========================================================
    query = f"""
    SELECT
        vl.list_id,
        vl.list_name,
        vl.active,
        vl.list_description,
        COUNT(DISTINCT vll.lead_id) as total_leads,
        SUM(CASE WHEN vll.called_count = 0 THEN 1 ELSE 0 END) as never_called,
        SUM(CASE WHEN vll.called_count > 0 THEN 1 ELSE 0 END) as called_before,
        MAX(vll.called_count) as max_called_count,
        AVG(vll.called_count) as avg_called_count
    FROM vicidial_lists vl
    LEFT JOIN vicidial_list vll ON vl.list_id = vll.list_id
    WHERE vl.campaign_id = '{CAMPAIGN_ID}'
    GROUP BY vl.list_id, vl.list_name, vl.active, vl.list_description
    ORDER BY vl.active DESC, total_leads DESC
    """
    results = execute_query(conn, query, "3. Active Lists Summary")
    data["active_lists"] = results

    # ========================================================
    # 4. STATUS DISTRIBUTION (Last 7 days)
    # ========================================================
    query = f"""
    SELECT
        status,
        COUNT(*) as count,
        ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 2) as percentage,
        ROUND(AVG(length_in_sec), 1) as avg_duration_sec,
        ROUND(SUM(length_in_sec)/60, 2) as total_minutes
    FROM vicidial_log
    WHERE campaign_id = '{CAMPAIGN_ID}'
    AND call_date >= DATE_SUB(NOW(), INTERVAL {DAYS_BACK} DAY)
    GROUP BY status
    ORDER BY count DESC
    """
    results = execute_query(conn, query, "4. Status Distribution")
    data["status_distribution"] = results

    # ========================================================
    # 5. HOURLY PERFORMANCE (with conversion metrics)
    # ========================================================
    query = f"""
    SELECT
        HOUR(call_date) as hour,
        COUNT(*) as total_calls,
        ROUND(AVG(length_in_sec), 1) as avg_duration,
        ROUND(SUM(length_in_sec)/60, 2) as total_minutes,
        SUM(CASE WHEN status = 'PU' THEN 1 ELSE 0 END) as pu_count,
        SUM(CASE WHEN status = 'SVYCLM' THEN 1 ELSE 0 END) as svyclm_count,
        ROUND(SUM(CASE WHEN status IN ('PU', 'SVYCLM') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as conversion_rate
    FROM vicidial_log
    WHERE campaign_id = '{CAMPAIGN_ID}'
    AND call_date >= DATE_SUB(NOW(), INTERVAL {DAYS_BACK} DAY)
    GROUP BY hour
    ORDER BY hour
    """
    results = execute_query(conn, query, "5. Hourly Performance")
    data["hourly_performance"] = results

    # ========================================================
    # 6. DAILY PERFORMANCE (Last 30 days)
    # ========================================================
    query = f"""
    SELECT
        DATE(call_date) as date,
        DAYNAME(call_date) as day_name,
        COUNT(*) as total_calls,
        ROUND(SUM(length_in_sec)/60, 2) as total_minutes,
        ROUND(SUM(length_in_sec)/60 * 0.0032, 2) as est_cost_fix,
        ROUND(SUM(length_in_sec)/60 * 0.0105, 2) as est_cost_mobile
    FROM vicidial_log
    WHERE campaign_id = '{CAMPAIGN_ID}'
    AND call_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY date, day_name
    ORDER BY date DESC
    LIMIT 30
    """
    results = execute_query(conn, query, "6. Daily Performance (30 days)")
    data["daily_performance"] = results

    # ========================================================
    # 7. PREFIX ANALYSIS
    # ========================================================
    query = f"""
    SELECT
        SUBSTRING(phone_number, 1, 2) as prefix_2,
        SUBSTRING(phone_number, 1, 3) as prefix_3,
        SUBSTRING(phone_number, 1, 4) as prefix_4,
        COUNT(*) as calls,
        ROUND(AVG(length_in_sec), 1) as avg_duration,
        ROUND(SUM(length_in_sec)/60, 2) as total_minutes
    FROM vicidial_log
    WHERE campaign_id = '{CAMPAIGN_ID}'
    AND call_date >= DATE_SUB(NOW(), INTERVAL {DAYS_BACK} DAY)
    AND phone_number IS NOT NULL
    AND phone_number != ''
    GROUP BY prefix_2, prefix_3, prefix_4
    HAVING calls > 50
    ORDER BY calls DESC
    LIMIT 150
    """
    results = execute_query(conn, query, "7. Prefix Analysis (Top 150)")
    data["prefix_analysis"] = results

    # ========================================================
    # 8. LIST PERFORMANCE BY LIST_ID
    # ========================================================
    query = f"""
    SELECT
        vll.list_id,
        COUNT(*) as calls,
        ROUND(AVG(vlog.length_in_sec), 1) as avg_duration,
        ROUND(SUM(vlog.length_in_sec)/60, 2) as total_minutes,
        COUNT(DISTINCT vlog.lead_id) as unique_leads,
        COUNT(DISTINCT vlog.phone_number) as unique_phones
    FROM vicidial_log vlog
    JOIN vicidial_list vll ON vlog.lead_id = vll.lead_id
    WHERE vlog.campaign_id = '{CAMPAIGN_ID}'
    AND vlog.call_date >= DATE_SUB(NOW(), INTERVAL {DAYS_BACK} DAY)
    GROUP BY vll.list_id
    ORDER BY calls DESC
    """
    results = execute_query(conn, query, "8. List Performance Comparison")
    data["list_performance"] = results

    # ========================================================
    # 9. LEAD RECYCLE STATUS
    # ========================================================
    query = f"""
    SELECT
        status,
        called_count,
        COUNT(*) as leads_count
    FROM vicidial_list
    WHERE list_id IN (
        SELECT list_id FROM vicidial_lists WHERE campaign_id = '{CAMPAIGN_ID}'
    )
    GROUP BY status, called_count
    ORDER BY called_count DESC, status
    LIMIT 100
    """
    results = execute_query(conn, query, "9. Lead Recycling Status")
    data["recycling_status"] = results

    # ========================================================
    # 10. CLOSER LOG (IVR Events - Last 7 days)
    # ========================================================
    query = f"""
    SELECT
        DATE(call_date) as date,
        status,
        COUNT(*) as count,
        ROUND(AVG(length_in_sec), 1) as avg_duration
    FROM vicidial_closer_log
    WHERE campaign_id = '{CAMPAIGN_ID}'
    AND call_date >= DATE_SUB(NOW(), INTERVAL {DAYS_BACK} DAY)
    GROUP BY date, status
    ORDER BY date DESC, count DESC
    """
    results = execute_query(conn, query, "10. Closer Log (IVR Press Events)")
    data["closer_log"] = results

    # ========================================================
    # 11. SAMPLE LEADS (to see structure)
    # ========================================================
    query = f"""
    SELECT *
    FROM vicidial_list
    WHERE list_id IN (
        SELECT list_id FROM vicidial_lists
        WHERE campaign_id = '{CAMPAIGN_ID}'
        AND active = 'Y'
        LIMIT 1
    )
    LIMIT 20
    """
    results = execute_query(conn, query, "11. Sample Leads Data")
    data["sample_leads"] = results

    # ========================================================
    # 12. CALL TIME CONFIG
    # ========================================================
    query = f"""
    SELECT ct.call_time_id, ct.call_time_name, ct.call_time_comments,
           cth.call_time_id, cth.start_hour, cth.start_min,
           cth.stop_hour, cth.stop_min, cth.day_of_week
    FROM vicidial_call_times ct
    LEFT JOIN vicidial_call_time_hours cth ON ct.call_time_id = cth.call_time_id
    WHERE ct.call_time_id = (
        SELECT local_call_time FROM vicidial_campaigns
        WHERE campaign_id = '{CAMPAIGN_ID}'
    )
    ORDER BY cth.day_of_week, cth.start_hour
    """
    results = execute_query(conn, query, "12. Call Time Configuration")
    data["call_time_config"] = results

    # ========================================================
    # 13. LEAD FILTER CONFIG
    # ========================================================
    query = f"""
    SELECT *
    FROM vicidial_lead_filters
    WHERE lead_filter_id = (
        SELECT lead_filter_id FROM vicidial_campaigns
        WHERE campaign_id = '{CAMPAIGN_ID}'
    )
    """
    results = execute_query(conn, query, "13. Lead Filter Config")
    data["lead_filter_config"] = results

    query = f"""
    SELECT *
    FROM vicidial_lead_filter_rules
    WHERE lead_filter_id = (
        SELECT lead_filter_id FROM vicidial_campaigns
        WHERE campaign_id = '{CAMPAIGN_ID}'
    )
    """
    results = execute_query(conn, query, "13b. Lead Filter Rules")
    data["lead_filter_rules"] = results

    # ========================================================
    # 14. HOPPER STATUS
    # ========================================================
    query = f"""
    SELECT
        list_id,
        COUNT(*) as leads_in_hopper,
        MIN(gmt_offset_now) as min_gmt,
        MAX(gmt_offset_now) as max_gmt,
        status,
        priority
    FROM vicidial_hopper
    WHERE campaign_id = '{CAMPAIGN_ID}'
    GROUP BY list_id, status, priority
    ORDER BY leads_in_hopper DESC
    """
    results = execute_query(conn, query, "14. Current Hopper Status")
    data["hopper_status"] = results

    # ========================================================
    # 15. PREFIX STATISTICS BY STATUS
    # ========================================================
    query = f"""
    SELECT
        SUBSTRING(phone_number, 1, 2) as prefix_2,
        SUBSTRING(phone_number, 1, 3) as prefix_3,
        status,
        COUNT(*) as calls,
        ROUND(AVG(length_in_sec), 1) as avg_duration,
        ROUND(SUM(length_in_sec)/60, 2) as total_minutes
    FROM vicidial_log
    WHERE campaign_id = '{CAMPAIGN_ID}'
    AND call_date >= DATE_SUB(NOW(), INTERVAL {DAYS_BACK} DAY)
    AND phone_number IS NOT NULL
    AND LENGTH(phone_number) >= 6
    GROUP BY prefix_2, prefix_3, status
    HAVING calls > 20
    ORDER BY prefix_2, prefix_3, calls DESC
    LIMIT 500
    """
    results = execute_query(conn, query, "15. Prefix + Status Analysis")
    data["prefix_status_analysis"] = results

    # ========================================================
    # 16. VICIDIAL STATUS NAMES
    # ========================================================
    query = f"""
    SELECT
        status, status_name, selectable, human_answered,
        sale, dnc, customer_contact, not_interested,
        scheduled_callback, completed
    FROM vicidial_campaign_statuses
    WHERE campaign_id = '{CAMPAIGN_ID}'
    ORDER BY status
    """
    results = execute_query(conn, query, "16. Campaign Status Definitions")
    data["status_definitions"] = results

    # Close connection
    conn.close()
    print("\n✅ Database connection closed")

    # ========================================================
    # SAVE TO JSON
    # ========================================================
    # Output file per DB key (e.g., vicidial_analysis_data_db.json)
    suffix = DB_KEY.replace("/", "_")
    output_file = f"vicidial_analysis_data_{suffix}.json"

    # Convert any non-serializable objects
    def convert_decimals(obj):
        """Convert Decimal to float for JSON serialization"""
        if isinstance(obj, list):
            return [convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_decimals(value) for key, value in obj.items()}
        elif hasattr(obj, '__float__'):
            return float(obj)
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return obj

    data = convert_decimals(data)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n{'='*60}")
    print(f"✅ DATA COLLECTION COMPLETED!")
    print(f"{'='*60}")
    print(f"📁 Output file: {output_file}")
    print(f"📊 Total sections: {len([k for k in data.keys() if k not in ['collection_date', 'campaign_id', 'db_key', 'analysis_period_days']])}")
    print(f"\n💡 Next step: Share this file and I'll build the Analyzer + Recommender!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

