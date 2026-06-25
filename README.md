# Food AI Search System

AI-powered food database search with Arabic + English support.

## Features

- 152 foods from Egyptian/Middle Eastern cuisine
- Arabic and English search (auto-detected)
- Bilingual display (name_en + name_ar)
- API key authentication
- REST API (GET/POST)
- CLI interface
- Background web scraper with pause/resume on user requests
- Search result caching (in-memory LRU + SQLite persistence)
- GZip compression
- Multi-device load balancing via ngrok (coordinator/worker mode)
- Database viewer web UI with SQL query editor
- TypeScript type definitions (`food_types.ts`)

## Setup

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# Start the server
python main.py serve

# Open in browser
# Dashboard: http://localhost:8000
# Database:  http://localhost:8000/db
# API Docs:  http://localhost:8000/docs
```

## Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLITE_PATH` | `foods.db` | SQLite database file path |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `OPENAI_API_KEY` | | OpenAI API key |
| `GEMINI_API_KEY` | | Google Gemini API key |
| `CLAUDE_API_KEY` | | Anthropic Claude API key |
| `OPENROUTER_API_KEY` | | OpenRouter API key |
| `DEEPSEEK_API_KEY` | | DeepSeek API key |
| `NVIDIA_API_KEY` | | NVIDIA API key |
| `AI_PROVIDER_PRIORITY` | `openai,gemini,claude,...` | AI provider priority order |
| `SCRAPER_TIMEOUT` | `30` | Web scraper timeout (seconds) |
| `BACKGROUND_SCRAPER_ENABLED` | `true` | Auto-start background scraper |
| `BACKGROUND_SCRAPER_BATCH_SIZE` | `10` | Foods per scraping batch |
| `BACKGROUND_SCRAPER_INTERVAL` | `300` | Seconds between batches |
| `CACHE_TTL` | `3600` | Cache time-to-live (seconds) |
| `CACHE_MAX_MEMORY` | `1000` | Max in-memory cache entries |
| `NODE_MODE` | `standalone` | `standalone`, `coordinator`, or `worker` |
| `COORDINATOR_URL` | | Coordinator server ngrok URL (worker mode) |
| `WORKER_NAME` | `worker-1` | Worker node name |
| `WORKER_NGROK_URL` | | This worker's ngrok URL |
| `HEALTH_CHECK_INTERVAL` | `15` | Seconds between worker health checks |
| `HEALTH_CHECK_TIMEOUT` | `5` | Health check timeout (seconds) |
| `HEALTH_CHECK_FAILURE_THRESHOLD` | `3` | Failures before marking worker inactive |
| `WORKER_HEARTBEAT_INTERVAL` | `30` | Seconds between worker heartbeats |

## Multi-Device Load Balancing

Connect multiple devices running Python + ngrok for distributed scraping:

**Main server (coordinator):**
```bash
# .env
NODE_MODE=coordinator
```
```bash
python main.py serve
```

**Worker device (behind ngrok):**
```bash
# .env
NODE_MODE=worker
COORDINATOR_URL=https://main-server.ngrok.io
WORKER_NAME=worker-laptop
WORKER_NGROK_URL=https://this-device.ngrok.io
```
```bash
python main.py serve
```

The coordinator distributes search requests across workers using round-robin. Workers register automatically and send heartbeats. Inactive workers are removed after 3 failed health checks.

## CLI Usage

```bash
# Search in English
python main.py search -q banana

# Search in Arabic
python main.py search -q موز

# Start API server
python main.py serve

# Start as coordinator
NODE_MODE=coordinator python main.py serve

# Start as worker
NODE_MODE=worker python main.py serve

# Generate API key
python main.py generate-key -n my-app

# List API keys
python main.py list-keys

# Bulk scrape from JSON file
python main.py bulk-scrape -f food_list.json

# Bulk scrape from text
python main.py bulk-scrape -t "banana,rice,chicken"

# Scrape a single food
python main.py scrape-single --name-en banana --name-ar موز
```

## API Endpoints

### Search (GET)
```bash
curl "http://localhost:8000/api/foods/search?q=banana"
```

### Search (POST)
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "banana"}' http://localhost:8000/api/foods/search
```

### List All Foods
```bash
curl http://localhost:8000/api/foods
```

### Add Food (auth required)
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"food_id":"kiwi","name_en":"Kiwi","name_ar":"كيوي","carbs":15}' \
  http://localhost:8000/api/foods
```

### Bulk Add Foods (auth required)
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '[{"name_en":"Kiwi","name_ar":"كيوي","carbs":15},{"name_en":"Mango","name_ar":"مانجو","carbs":14}]' \
  http://localhost:8000/api/foods/bulk
```

### Delete Food (auth required)
```bash
curl -X DELETE -H "X-API-Key: your-key" http://localhost:8000/api/foods/kiwi
```

### Database Viewer
```
GET  /db                     Web UI for browsing the database
GET  /api/db/stats           Database statistics
GET  /api/db/tables          List all tables
GET  /api/db/table/{name}    Paginated table data
GET  /api/db/table/{name}/schema  Table schema
POST /api/db/query           Run read-only SQL query
```

### Cache
```
GET  /api/cache/stats        Cache hit rate and entry counts
POST /api/cache/invalidate   Clear all cached results (auth required)
```

### Scraper Control
```
GET  /api/scraper/status     Background scraper status
POST /api/scraper/start      Start background scraper
POST /api/scraper/stop       Stop background scraper
```

### Worker Management (coordinator mode)
```
GET    /api/workers                List all workers
POST   /api/workers/register       Register a worker
DELETE /api/workers/{name}         Deregister a worker
POST   /api/workers/{name}/heartbeat  Worker heartbeat
GET    /api/workers/{name}/status  Worker status
GET    /api/coordinator/health     Coordinator health check
GET    /api/worker/info            Worker node info
```

### TypeScript Types
```typescript
import { Food, FoodResponse, API, searchFoods } from './food_types';
```

## Response Format

```json
{
  "success": true,
  "query": "موز",
  "lang": "ar",
  "results": [
    {
      "food_id": "banana",
      "name_en": "Banana",
      "name_ar": "موز",
      "carbs": 27.0,
      "category_en": "Fruits",
      "category_ar": "فواكه",
      "serving_description": "1 medium (118g)"
    }
  ],
  "message": "تم العثور على نتيجة واحدة"
}
```

# Made By Demo

## for my brother
