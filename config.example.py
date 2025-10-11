"""
Example configuration file for the vicidial_agent project.

This file contains placeholder values and does not include any real credentials.
Copy this file to `config.py` (which is ignored by version control) and fill in
your own database and API credentials locally.
"""

# Example Vicidial database configuration
VICIDIAL_DB = {
    "host": "your-db-host.example.com",
    "port": 3306,
    "user": "your_db_username",
    "password": "your_db_password",
    "database": "asterisk"
}

# Web credentials for accessing Vicidial recordings (if required)
VICIDIAL_WEB = {
    "username": "your_web_username",
    "password": "your_web_password"
}

# Google API configuration
GOOGLE = {
    # Path to your service account JSON file (not tracked by git)
    "service_account_json": "service-account.json",
    # Spreadsheet ID and range for reading phone numbers
    "sheet_id": "your_google_sheet_id",
    "range": "A2:A",
    # Folder ID on Google Drive where recordings will be uploaded
    "drive_folder_id": "your_drive_folder_id"
}

# Parameters controlling the downloader
PARAMS = {
    "match_last_n_digits": 9,
    "duration_min_sec": 240,
    "duration_max_sec": 360,
    "total_limit": 20,
    "optional_date_from": "",
    "optional_date_to": ""
}
