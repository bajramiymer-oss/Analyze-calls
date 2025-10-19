"""
core/constants.py

Global constants for the entire project.
Modify here instead of searching through multiple files.

Author: Protrade AI
Last Updated: 2025-10-13
"""

from typing import Set, Dict

# ============== AUDIO FORMATS ==============
AUDIO_EXTENSIONS: Set[str] = {
    ".mp3",
    ".wav",
    ".m4a",
    ".mp4",
    ".ogg",
    ".flac"
}

TEXT_EXTENSIONS: Set[str] = {
    ".txt",
    ".docx"
}

DOCUMENT_EXTENSIONS: Set[str] = {
    ".pdf",
    ".docx",
    ".txt"
}

# ============== FOLDER NAMES TO IGNORE ==============
# Used for agent name detection - skip these common folder names
COMMON_BAD_FOLDERS: Set[str] = {
    "new folder",
    "documents",
    "downloads",
    "desktop",
    "vicidial_agent",
    "data",
    "out_analysis",
    "audio",
    "records",
    "regjistrime",
    "tmp",
    "temp",
    "cache"
}

# ============== CAMPAIGN LIMITS ==============
# Maximum documents per campaign
MAX_DOCUMENTS_PER_CAMPAIGN: int = 3

# Maximum file size in MB
MAX_FILE_SIZE_MB: int = 5

# Maximum total pages across all documents
MAX_TOTAL_PAGES: int = 50

# ============== LANGUAGE SETTINGS ==============
# Language codes and display names
LANGUAGE_MAP: Dict[str, str] = {
    "Shqip": "sq",
    "Italisht": "it",
    "Anglisht": "en"
}

# Full language names for prompts
LANGUAGE_NAMES: Dict[str, str] = {
    "sq": "shqip",
    "it": "italisht",
    "en": "anglisht"
}

# ============== DATABASE CONFIGURATION ==============
# Database connection keys
DB_KEYS: Dict[str, str] = {
    "db": "Database 1",
    "db2": "Database 2"
}

# Default database key
DEFAULT_DB_KEY: str = "db"

# ============== OPENAI SETTINGS ==============
# Default model for analysis
DEFAULT_ANALYSIS_MODEL: str = "gpt-4.1"

# Default model for transcription
DEFAULT_TRANSCRIPTION_MODEL: str = "gpt-4o-transcribe"

# Fallback model for transcription
FALLBACK_TRANSCRIPTION_MODEL: str = "whisper-1"

# Maximum transcript length for analysis (characters)
MAX_TRANSCRIPT_LENGTH: int = 50_000

# ============== VICIDIAL STATUS CODES ==============
# All possible Vicidial status codes
ALL_VICIDIAL_STATUSES: Set[str] = {
    "AA", "AB", "ADC", "AFAX", "AL", "AM", "A",
    "B", "BUSY",
    "CALLBK", "CBHOLD", "CPTERR",
    "DC", "DEC", "DISCONN", "DNC", "DROP", "DROPHG",
    "ERI", "ERRVM",
    "IVRXFR",
    "LAGGED", "LB", "LRERR",
    "MAXCALL", "MLINAT", "MLIVEO", "MLVMCT", "MLVMEO",
    "NA", "NANQUE", "NCALL", "NOINT", "N",
    "PAMD", "PDROP", "PM", "PU",
    "QVMAIL",
    "RQXFER",
    "SALE", "SVYCLM",
    "TIMEOT", "XDROP", "XFER"
}

# Success statuses (for reporting)
SUCCESS_STATUSES: Set[str] = {
    "SALE", "CALLBK", "A", "B"
}

# ============== FILE PATHS ==============
# Template file for LLM prompts
PROMPT_TEMPLATE_FILENAME: str = "prompt_analysis_template.txt"

# Campaign contexts configuration
CAMPAIGN_CONFIG_FILENAME: str = "campaign_contexts.json"

# General settings configuration
SETTINGS_CONFIG_FILENAME: str = "settings.json"

# VoIP rates configuration
VOIP_RATES_FILENAME: str = "voip_rates.json"

# ============== OUTPUT SETTINGS ==============
# Default output directory name
DEFAULT_OUTPUT_DIR: str = "out_analysis"

# Subdirectory for transcripts
TRANSCRIPTS_SUBDIR: str = "Transkripte"

# Output file names
CALL_ANALYSIS_CSV: str = "call_analysis.csv"
AGENT_SUMMARY_CSV: str = "agent_summary_weekly.csv"
REPORT_EXCEL: str = "Raport_Analize.xlsx"

# ============== AGENT SCORING ==============
# Positive keywords for scoring (increases score)
POSITIVE_KEYWORDS: Set[str] = {
    # English
    "clear", "empat", "active", "listening", "polite", "professional",
    "friendly", "helpful", "patient", "courteous", "respectful",
    # Albanian
    "qart", "empatik", "degjim", "sjellshem", "profesional",
    "miqesor", "ndihmues", "durimtar", "respektues",
    # Italian
    "chiaro", "empatico", "ascolto", "professionale", "cortese",
    "amichevole", "paziente", "rispettoso"
}

# Negative keywords for scoring (decreases score)
NEGATIVE_KEYWORDS: Set[str] = {
    # English
    "interrupt", "confus", "aggressive", "pushy", "weak closing",
    "unprofessional", "rude", "impatient", "unclear",
    # Albanian
    "nderpret", "konfuz", "agresiv", "mungese mbyllje",
    "joprofesional", "vrazhdë", "padurimtar", "joqartë",
    # Italian
    "interrompe", "confuso", "aggressivo", "debole chiusura",
    "maleducato", "impaziente", "poco chiaro"
}

# Score range
MIN_SCORE: float = 1.0
MAX_SCORE: float = 5.0
DEFAULT_SCORE: float = 3.0

# ============== REPORT SETTINGS ==============
# Smart Reports - Cost Analysis defaults
DEFAULT_MOBILE_RATE: float = 0.018  # €/min
DEFAULT_FIX_RATE: float = 0.008     # €/min

# Default status costs (€ per call)
DEFAULT_STATUS_COSTS: Dict[str, float] = {
    "SALE": 0.15,
    "CALLBK": 0.05,
    "A": 0.08,
    "B": 0.08,
    "NI": 0.02,
    "NA": 0.02,
    "DROP": 0.01
}

# Resa threshold percentage (for list quality)
DEFAULT_RESA_THRESHOLD: float = 5.0

# ============== UI SETTINGS ==============
# Progress bar update frequency
PROGRESS_UPDATE_INTERVAL: int = 1  # Update every N items

# Maximum items to display in lists
MAX_DISPLAY_ITEMS: int = 100

# Session expiry (minutes)
SESSION_EXPIRY_MINUTES: int = 60

# ============== VALIDATION RULES ==============
# Campaign name validation
MIN_CAMPAIGN_NAME_LENGTH: int = 3
MAX_CAMPAIGN_NAME_LENGTH: int = 100

# Agent name validation
MIN_AGENT_NAME_LENGTH: int = 2
MAX_AGENT_NAME_LENGTH: int = 50

# Session name validation
MIN_SESSION_NAME_LENGTH: int = 1
MAX_SESSION_NAME_LENGTH: int = 100

# ============== ERROR MESSAGES ==============
# Common error messages (for consistency)
ERROR_NO_OPENAI_KEY: str = "OPENAI_API_KEY mungon. Vendose në secrets.toml ose environment variable."
ERROR_NO_DB_CONNECTION: str = "Nuk u lidh me databazën Vicidial. Kontrollo credentials dhe VPN."
ERROR_NO_AUDIO_FILES: str = "S'u gjet asnjë file audio në atë folder."
ERROR_NO_TRANSCRIPTS: str = "S'u krijua asnjë transkript. Kontrollo log-et për gabime."
ERROR_CAMPAIGN_NOT_FOUND: str = "Kampanja nuk u gjet. Krijoje fillimisht te Settings."
ERROR_DOCUMENT_LIMIT: str = f"Mund të ngarkoni maksimumi {MAX_DOCUMENTS_PER_CAMPAIGN} dokumente për fushatë."
ERROR_FILE_TOO_LARGE: str = f"File-i është shumë i madh (max {MAX_FILE_SIZE_MB}MB)."

# Success messages
SUCCESS_PIPELINE_COMPLETE: str = "✅ Pipeline u përfundua me sukses!"
SUCCESS_CAMPAIGN_CREATED: str = "✅ Kampanja u krijua me sukses!"
SUCCESS_DOCUMENT_UPLOADED: str = "✅ Dokumenti u ngarkua me sukses!"

# ============== HELPER FUNCTIONS ==============

def get_language_name(code: str) -> str:
    """
    Convert language code to full name.

    Args:
        code: Language code ("sq", "it", "en")

    Returns:
        Full language name or default to "shqip"

    Example:
        >>> get_language_name("en")
        'anglisht'
    """
    return LANGUAGE_NAMES.get(code, "shqip")


def get_language_code(label: str) -> str:
    """
    Convert language label to code.

    Args:
        label: Language label ("Shqip", "Italisht", "Anglisht")

    Returns:
        Language code or default to "sq"

    Example:
        >>> get_language_code("Anglisht")
        'en'
    """
    return LANGUAGE_MAP.get(label, "sq")


def is_audio_file(filename: str) -> bool:
    """
    Check if filename has audio extension.

    Args:
        filename: File name or path

    Returns:
        True if audio file, False otherwise

    Example:
        >>> is_audio_file("recording.mp3")
        True
        >>> is_audio_file("transcript.txt")
        False
    """
    from pathlib import Path
    return Path(filename).suffix.lower() in AUDIO_EXTENSIONS


def is_text_file(filename: str) -> bool:
    """
    Check if filename has text extension.

    Args:
        filename: File name or path

    Returns:
        True if text file, False otherwise
    """
    from pathlib import Path
    return Path(filename).suffix.lower() in TEXT_EXTENSIONS


def is_document_file(filename: str) -> bool:
    """
    Check if filename has document extension (for campaigns).

    Args:
        filename: File name or path

    Returns:
        True if document file, False otherwise
    """
    from pathlib import Path
    return Path(filename).suffix.lower() in DOCUMENT_EXTENSIONS


# ============== VERSION INFO ==============
VERSION: str = "2.0.0"
BUILD_DATE: str = "2025-10-13"
AUTHOR: str = "Protrade AI"

















