# local_vici_downloader_oauth.py
import os, io, re, csv
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import mysql.connector as mysql

# OAuth user creds
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GARequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Sheets via OAuth user creds
import gspread

from config import VICIDIAL_DB, VICIDIAL_WEB, GOOGLE, PARAMS

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

def normalize_phone(s): 
    return re.sub(r"\D+", "", s or "")

def get_user_oauth_creds():
    """
    Përdor OAuth si përdorues (Gmail).
    Kërkon 'credentials.json' dhe krijon/lexon 'token.json'.
    """
    cred_path = os.path.abspath("credentials.json")
    token_path = os.path.abspath("token.json")
    creds = None

    if os.path.exists(token_path):
        creds = UserCredentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # rifresko tokenin nëse ke refresh_token
            creds.refresh(GARequest())
        else:
            # hap browser-in lokalisht dhe përfundo login-in
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            # port=0 zgjedh automatikisht një port të lirë; open_browser=True hap automatikisht shfletuesin
            creds = flow.run_local_server(port=0, open_browser=True, prompt="consent")
        # ruaj token.json për përdorimet e ardhshme
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds

def load_numbers_from_sheet(creds):
    print("[INFO] Po lexoj numrat nga Google Sheet (OAuth)...")
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(GOOGLE["sheet_id"])
    values = sheet.values_get(GOOGLE["range"]).get("values", [])
    nums, seen = [], set()
    for row in values:
        if not row:
            continue
        n = normalize_phone(row[0])
        if n and n not in seen:
            seen.add(n); nums.append(n)
    print(f"[INFO] U gjetën {len(nums)} numra unikë në fletë.")
    return nums

def connect_db():
    print("[INFO] Po lidhem me MySQL...")
    return mysql.connect(**VICIDIAL_DB)

def http_get(url):
    if VICIDIAL_WEB.get("username") and VICIDIAL_WEB.get("password"):
        return requests.get(url, auth=(VICIDIAL_WEB["username"], VICIDIAL_WEB["password"]), timeout=60)
    return requests.get(url, timeout=60)

def chunk(arr, size=200):
    for i in range(0, len(arr), size):
        yield arr[i:i+size]

def build_lead_map(cursor, suffix_map):
    """
    Gjen lead_id për numrat duke bërë match te N shifrat e fundit (RIGHT(...,N)),
    pa skanuar gjithë tabelën.
    """
    if not suffix_map:
        print("[WARN] Nuk ka sufikse për kërkim."); 
        return {}

    lengths = {len(k) for k in suffix_map.keys()}
    N = min(lengths) if lengths else 0
    if N == 0:
        print("[WARN] Gjatësia e sufiksit doli 0."); 
        return {}

    print(f"[INFO] Po kërkoj lead_id me match në {len(suffix_map)} sufikse (N={N} shifra të fundit)...")

    lead_map = {owner: set() for owners in suffix_map.values() for owner in owners}
    keys = list(suffix_map.keys())

    for batch in chunk(keys, size=200):
        ph = ",".join(["%s"] * len(batch))
        q = f"""
            SELECT lead_id, phone_number
            FROM vicidial_list
            WHERE phone_number REGEXP '^[0-9]+$'
              AND RIGHT(phone_number, {N}) IN ({ph})
        """
        cursor.execute(q, batch)
        for lead_id, phone in cursor.fetchall():
            p = normalize_phone(phone)
            if not p: 
                continue
            suf = p[-N:] if len(p) >= N else p
            for owner in suffix_map.get(suf, []):
                lead_map[owner].add(lead_id)

    total = sum(len(s) for s in lead_map.values())
    print(f"[INFO] Gjetëm gjithsej {total} lead_id që përputhen me numrat.")
    return lead_map

def query_recordings(cursor, lead_ids, p):
    if not lead_ids: 
        return []
    ids = ",".join(str(x) for x in lead_ids)
    q = f"""
        SELECT recording_id, lead_id, filename, location, length_in_sec, start_time, user
        FROM recording_log
        WHERE lead_id IN ({ids})
          AND length_in_sec BETWEEN {p["duration_min_sec"]} AND {p["duration_max_sec"]}
    """
    if p["optional_date_from"]:
        q += f" AND start_time >= '{p['optional_date_from']}'"
    if p["optional_date_to"]:
        q += f" AND start_time <= '{p['optional_date_to']}'"
    q += " ORDER BY start_time DESC"
    cursor.execute(q)
    return cursor.fetchall()

def ensure_drive_folder(service, parent_id, name):
    # My Drive (jo Shared drives): nuk duhen flags speciale
    q = f"'{parent_id}' in parents and name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    res = service.files().list(q=q, fields="files(id,name)").execute()
    files = res.get("files", [])
    if files: 
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    return service.files().create(body=meta, fields="id").execute()["id"]

def drive_upload_binary(service, folder_id, filename, content_bytes):
    media = MediaIoBaseUpload(io.BytesIO(content_bytes), mimetype="application/octet-stream", resumable=False)
    meta = {"name": filename, "parents": [folder_id]}
    return service.files().create(body=meta, media_body=media, fields="id").execute()["id"]

def main():
    # 1) OAuth si përdorues (Gmail) & Drive client
    creds = get_user_oauth_creds()
    drive = build("drive", "v3", credentials=creds)

    # 2) Lexo numrat nga Sheets me të njëjtat creds
    numbers = load_numbers_from_sheet(creds)
    if not numbers:
        print("[WARN] S'ka numra në Google Sheet.")
        return

    # 3) Përgatit sufikset sipas match_last_n_digits
    n_last = PARAMS["match_last_n_digits"]
    suffix_map = {}
    for n in numbers:
        suf = n[-n_last:] if len(n) >= n_last else n
        suffix_map.setdefault(suf, []).append(n)

    # 4) Përgatit folderët në Drive
    parent_folder_id = GOOGLE["drive_folder_id"]  # folder në My Drive që të përket ty
    session_name = f"Vicidial_20x5min_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')}"
    session_folder = ensure_drive_folder(drive, parent_folder_id, session_name)
    print(f"[INFO] Folder i sesionit në Drive: {session_name}")

    # 5) Lidhje DB dhe gjetje lead_id për numrat
    conn = connect_db()
    cur = conn.cursor()
    lead_map = build_lead_map(cur, suffix_map)

    # 6) Shkarko & ngarko regjistrimet (deri në total_limit)
    total_downloaded = 0
    total_limit = PARAMS["total_limit"]
    print(f"[INFO] Filloj shkarkimin. Limit total: {total_limit} skedarë.")

    for owner_num, owner_leads in lead_map.items():
        if total_downloaded >= total_limit:
            break
        if not owner_leads:
            print(f"[INFO] {owner_num}: s'u gjet asnjë lead_id.")
            continue

        owner_folder = ensure_drive_folder(drive, session_folder, owner_num)
        manifest_rows = [["recording_id","lead_id","filename","saved_as","location","length_in_sec","start_time","user","status"]]

        lst = list(owner_leads)
        for batch in chunk(lst, size=800):
            if total_downloaded >= total_limit:
                break
            rows = query_recordings(cur, batch, PARAMS)
            print(f"[INFO] {owner_num}: u gjetën {len(rows)} regjistrime në këtë batch.")

            for (rec_id, lead_id, filename, location, length, start_time, user) in rows:
                if total_downloaded >= total_limit:
                    break
                status = "SKIPPED"; saved_name = ""

                if location and location.lower().startswith(("http://", "https://")):
                    try:
                        r = http_get(location)
                        if r.status_code == 200:
                            ts = (start_time.strftime("%Y%m%d_%H%M%S") if hasattr(start_time, "strftime")
                                  else str(start_time).replace(" ", "_").replace(":",""))
                            base = filename or os.path.basename(urlparse(location).path) or f"{rec_id}.wav"
                            saved_name = f"{ts}_{base}"
                            drive_upload_binary(drive, owner_folder, saved_name, r.content)
                            status = "OK"; total_downloaded += 1
                            print(f"[OK]  {owner_num} -> {saved_name} (total={total_downloaded})")
                        else:
                            status = f"HTTP {r.status_code}"
                            print(f"[HTTP] {owner_num} -> {location} => {status}")
                    except Exception as e:
                        status = f"ERR {e}"
                        print(f"[ERR] {owner_num} -> {location} => {status}")
                else:
                    status = "Unsupported or empty location"
                    print(f"[WARN] {owner_num} -> location jo http/https: {location}")

                manifest_rows.append([rec_id, lead_id, filename, saved_name, location, length, str(start_time), user, status])
                if total_downloaded >= total_limit:
                    break

        # manifest.csv për këtë numër
        csv_buf = io.StringIO(); w = csv.writer(csv_buf)
        for row in manifest_rows: w.writerow(row)
        drive_upload_binary(drive, owner_folder, "manifest.csv", csv_buf.getvalue().encode("utf-8"))

    cur.close(); conn.close()
    print(f"[DONE] U ngarkuan {total_downloaded} skedarë në Drive. Folder sesioni: {session_name}")

if __name__ == "__main__":
    main()
