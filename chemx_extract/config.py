import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NOT_DETECTED = "NOT_DETECTED"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-2024-11-20")
PUBCHEM_USER_AGENT = os.getenv("PUBCHEM_USER_AGENT", "DataCon2026/1.0")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "out"))
