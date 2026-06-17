import os
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_PATH", "foods.db")
API_KEY_HEADER = "X-API-Key"
API_KEYS_FILE = "api_keys.json"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
