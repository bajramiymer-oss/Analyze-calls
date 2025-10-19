"""Quick check for IVR Press 1 responses"""
import pymysql
import pathlib

try:
    import tomllib
except:
    import tomli as tomllib

secrets = tomllib.load(open(".streamlit/secrets.toml", "rb"))
db = secrets["db2"]

conn = pymysql.connect(
    host=db["host"],
    user=db["user"],
    password=db["password"],
    database=db["database"],
    charset='utf8mb4'
)

cur = conn.cursor()

# Check IVR responses
print("\n📊 IVR Responses (Last 30 days):")
print("="*60)
cur.execute("""
    SELECT response, COUNT(*) as count
    FROM vicidial_ivr_response
    WHERE campaign = 'autobiz'
    AND created >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY response
    ORDER BY count DESC
""")

for row in cur.fetchall():
    print(f"{row[0]}: {row[1]:,}")

print("\n📅 Daily Press 1 (Last 14 days):")
print("="*60)
cur.execute("""
    SELECT DATE(created) as date, response, COUNT(*) as count
    FROM vicidial_ivr_response
    WHERE campaign = 'autobiz'
    AND created >= DATE_SUB(NOW(), INTERVAL 14 DAY)
    GROUP BY date, response
    ORDER BY date DESC, count DESC
""")

for row in cur.fetchall():
    print(f"{row[0]} - {row[1]}: {row[2]:,}")

conn.close()
print("\n✅ Done!")
















