import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = str(DATA_DIR / "customers.db")
CHROMA_PATH = str(DATA_DIR / "chroma_db")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-20250514"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "policy_documents"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)
