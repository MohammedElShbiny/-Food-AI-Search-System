import os
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_PATH", "foods.db")
API_KEY_HEADER = "X-API-Key"
API_KEYS_FILE = "api_keys.json"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

AI_PROVIDER_PRIORITY = os.getenv(
    "AI_PROVIDER_PRIORITY", "openai,gemini,claude,openrouter,deepseek,nvidia"
).split(",")

SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "10"))

EDAMAM_APP_ID = os.getenv("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY", "")

BULK_SCRAPER_CONCURRENCY = int(os.getenv("BULK_SCRAPER_CONCURRENCY", "5"))
BULK_SCRAPER_DELAY = float(os.getenv("BULK_SCRAPER_DELAY", "0.5"))

BACKGROUND_SCRAPER_ENABLED = os.getenv("BACKGROUND_SCRAPER_ENABLED", "false").lower() == "true"
BACKGROUND_SCRAPER_BATCH_SIZE = int(os.getenv("BACKGROUND_SCRAPER_BATCH_SIZE", "10"))
BACKGROUND_SCRAPER_INTERVAL = int(os.getenv("BACKGROUND_SCRAPER_INTERVAL", "300"))

NODE_MODE = os.getenv("NODE_MODE", "standalone")  # standalone | coordinator | worker
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "")
WORKER_NAME = os.getenv("WORKER_NAME", "worker-1")
WORKER_NGROK_URL = os.getenv("WORKER_NGROK_URL", "")

HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "15"))
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))
HEALTH_CHECK_FAILURE_THRESHOLD = int(os.getenv("HEALTH_CHECK_FAILURE_THRESHOLD", "3"))
WORKER_HEARTBEAT_INTERVAL = int(os.getenv("WORKER_HEARTBEAT_INTERVAL", "30"))

CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
CACHE_MAX_MEMORY = int(os.getenv("CACHE_MAX_MEMORY", "1000"))
