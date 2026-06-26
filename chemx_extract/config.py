import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NOT_DETECTED = "NOT_DETECTED"

# --- Anthropic ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_CHEAP_MODEL = os.getenv("ANTHROPIC_CHEAP_MODEL", "claude-haiku-4-5")
ANTHROPIC_EXTRACT_MODEL = os.getenv("ANTHROPIC_EXTRACT_MODEL", "claude-opus-4-8")
ANTHROPIC_MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "16000"))
ANTHROPIC_CHEAP_MAX_TOKENS = int(os.getenv("ANTHROPIC_CHEAP_MAX_TOKENS", "8192"))

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_CHEAP_MODEL = os.getenv("OPENAI_CHEAP_MODEL", "gpt-4o-mini")
OPENAI_EXTRACT_MODEL = os.getenv("OPENAI_EXTRACT_MODEL", "gpt-4.1-2025-04-14")
OPENAI_DRAFT_VISION_MODEL = os.getenv("OPENAI_DRAFT_VISION_MODEL", "gpt-4o-mini")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

PUBCHEM_USER_AGENT = os.getenv("PUBCHEM_USER_AGENT", "DataCon2026/1.0")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "out"))
