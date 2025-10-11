import os
import io
from typing import Optional, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GARequest
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES_RW = ["https://www.googleapis.com/auth/drive"]
SCOPES_RO = ["https://www.googleapis.com/auth/drive.readonly"]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def _load_creds_from_file(scopes):
    if os.path.exists(TOKEN_FILE):
        try:
            return Credentials.from_authorized_user_file(TOKEN_FILE, scopes)
        except Exception:
            return None
    return None

def _interactive_flow(scopes):
    if not os.path.exists(CREDENTIALS_FILE):
        raise RuntimeError("Mungon credentials.json në root-in e aplikacionit.")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, scopes)
    return flow.run_local_server(port=0)

def get_user_oauth_creds(readonly: bool = False) -> Credentials:
    scopes = SCOPES_RO if readonly else SCOPES_RW
    creds: Optional[Credentials] = _load_creds_from_file(scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GARequest())
            except Exception:
                creds = None  # do a new flow
        if not creds:
            creds = _interactive_flow(scopes)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

def force_reauth(readonly: bool = False) -> Credentials:
    """Fshin token.json dhe nis rrjedhën interaktive për re-auth."""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
    except Exception:
        pass
    return get_user_oauth_creds(readonly=readonly)

def ensure_folder(service, parent_id: str, name: str) -> str:
    q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed = false"
    resp = service.files().list(q=q, fields="files(id,name)", pageSize=1).execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    f = service.files().create(body=meta, fields="id").execute()
    return f["id"]

def ensure_path(service, parent_id: str, path_segments: List[str]) -> str:
    cur = parent_id
    for seg in path_segments:
        seg = seg.strip().replace("/", "-")
        cur = ensure_folder(service, cur, seg)
    return cur

def upload_file(service, parent_id: str, local_path: str, mime_type: str = None) -> str:
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    body = {"name": os.path.basename(local_path), "parents": [parent_id]}
    f = service.files().create(body=body, media_body=media, fields="id").execute()
    return f["id"]
