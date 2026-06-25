# Food AI - Complete Commands Reference

## Table of Contents

1. [CLI Commands](#1-cli-commands)
2. [API Endpoints](#2-api-endpoints)
3. [Environment Variables](#3-environment-variables)
4. [Multi-Device Setup](#4-multi-device-setup)
5. [Request/Response Examples](#5-requestresponse-examples)

---

## 1. CLI Commands

Run these from terminal in the `food_ai` folder.

### Start Server

```bash
python main.py serve
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind |
| `--port` | `8000` | Port to bind |

**Examples:**

```bash
python main.py serve                                    # Default
python main.py serve --host 127.0.0.1 --port 3000       # Custom host/port
NODE_MODE=coordinator python main.py serve              # As coordinator
NODE_MODE=worker python main.py serve                   # As worker
```

---

### Search Food

```bash
python main.py search -q "banana"
```

| Option | Required | Description |
|--------|----------|-------------|
| `-q, --query` | Yes | Food name (English or Arabic) |

**Examples:**

```bash
python main.py search -q banana          # English search
python main.py search -q موز             # Arabic search
python main.py search -q rice            # Partial match
python main.py search -q chicken         # Multiple results
```

**Output:**

```
Found 1 result(s) for 'banana':

  Banana (موزة)
    Carbs:    27.0g
    Category: Fruits
    Serving:  1 medium (118g)
```

---

### Generate API Key

```bash
python main.py generate-key -n "my-app"
```

| Option | Required | Description |
|--------|----------|-------------|
| `-n, --name` | Yes | Key name/label |

**Output:**

```
API Key Generated:
  Name: my-app
  Key:  food_ai_5521c11e38f343df9d6dfcd602bc714d
  Created: 2026-06-17T19:03:43.932046

Save this key - it won't be shown again!
```

---

### List API Keys

```bash
python main.py list-keys
```

**Output:**

```
API Keys:

  my-app: food_ai_5521c11e38f3... (active)
  test:   food_ai_ee17e7f0a730... (active)
```

---

### Bulk Scrape

Scrape carb data from multiple food websites for a list of foods.

```bash
python main.py bulk-scrape -f food_list.json
```

| Option | Required | Description |
|--------|----------|-------------|
| `-f, --file` | Yes* | JSON file with food list |
| `-t, --text` | Yes* | Comma-separated food names |
| `-c, --concurrency` | No | Max concurrent tasks (default: 5) |
| `-d, --delay` | No | Delay between requests in seconds (default: 0.5) |
| `-o, --output` | No | Save results report to JSON file |
| `--dry-run` | No | Don't write to database |

*Either `--file` or `--text` is required.

**Examples:**

```bash
python main.py bulk-scrape -f food_list.json
python main.py bulk-scrape -f food_list.json -c 10 -d 0.2
python main.py bulk-scrape -t "banana,rice,chicken" --dry-run
python main.py bulk-scrape -f food_list.json -o report.json
```

---

### Scrape Single Food

Scrape one food item from all sources.

```bash
python main.py scrape-single --name-en banana --name-ar موز
```

| Option | Required | Description |
|--------|----------|-------------|
| `--name-en` | Yes | English food name |
| `--name-ar` | No | Arabic food name |

**Output:**

```
Scraping: banana (موز) from all sources...

  Best result: 27.0g carbs (usda)
  Sources tried: 10
  Sources succeeded: 3
  Duration: 2.45s
```

---

## 2. API Endpoints

Base URL: `http://localhost:8000`

### Search Foods (GET)

```
GET /api/foods/search?q={query}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `q` | Yes | Search query (English or Arabic) |

**Auth:** Not required

**Example:**

```bash
curl "http://localhost:8000/api/foods/search?q=banana"
curl "http://localhost:8000/api/foods/search?q=موز"
```

---

### Search Foods (POST)

```
POST /api/foods/search
```

| Field | Required | Description |
|-------|----------|-------------|
| `query` | Yes | Search query |
| `lang` | No | Force language: `en` or `ar` (default: auto-detect) |

**Auth:** Not required

**Example:**

```bash
curl -X POST http://localhost:8000/api/foods/search \
  -H "Content-Type: application/json" \
  -d '{"query": "banana"}'

curl -X POST http://localhost:8000/api/foods/search \
  -H "Content-Type: application/json" \
  -d '{"query": "banana", "lang": "ar"}'
```

---

### List All Foods

```
GET /api/foods
```

**Auth:** Not required

**Example:**

```bash
curl http://localhost:8000/api/foods
```

---

### Add Food

```
POST /api/foods
```

| Field | Required | Description |
|-------|----------|-------------|
| `food_id` | No | Unique ID (auto-generated if omitted) |
| `name_en` | Yes | English name |
| `name_ar` | Yes | Arabic name |
| `carbs` | Yes | Carbs per serving (grams) |
| `category_en` | No | English category |
| `category_ar` | No | Arabic category |
| `serving_description` | No | Serving info |

**Auth:** Required (`X-API-Key` header)

**Example:**

```bash
curl -X POST http://localhost:8000/api/foods \
  -H "Content-Type: application/json" \
  -H "X-API-Key: food_ai_5521c11e38f343df9d6dfcd602bc714d" \
  -d '{
    "food_id": "kiwi",
    "name_en": "Kiwi",
    "name_ar": "كيوي",
    "carbs": 15.0,
    "category_en": "Fruits",
    "category_ar": "فواكه",
    "serving_description": "1 medium"
  }'
```

---

### Bulk Add Foods

```
POST /api/foods/bulk
```

**Auth:** Required (`X-API-Key` header)

**Example:**

```bash
curl -X POST http://localhost:8000/api/foods/bulk \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '[
    {"name_en": "Kiwi", "name_ar": "كيوي", "carbs": 15},
    {"name_en": "Mango", "name_ar": "مانجو", "carbs": 14}
  ]'
```

**Response:**

```json
{"success": true, "added": 2, "skipped": 0, "total": 2}
```

---

### Delete Food

```
DELETE /api/foods/{food_id}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `food_id` | Yes | Food ID to delete |

**Auth:** Required (`X-API-Key` header)

**Example:**

```bash
curl -X DELETE http://localhost:8000/api/foods/kiwi \
  -H "X-API-Key: food_ai_5521c11e38f343df9d6dfcd602bc714d"
```

---

### Generate API Key (HTTP)

```
POST /api/auth/key
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Key name/label |

**Auth:** Not required

**Example:**

```bash
curl -X POST http://localhost:8000/api/auth/key \
  -H "Content-Type: application/json" \
  -d '{"name": "my-mobile-app"}'
```

---

### Health Check

```
GET /api/health
```

**Auth:** Not required

**Example:**

```bash
curl http://localhost:8000/api/health
```

**Response:**

```json
{
  "status": "healthy",
  "service": "Food AI Search API",
  "version": "2.0.0"
}
```

---

### Database Viewer

```
GET  /db                           Web UI for browsing the database
GET  /api/db/stats                 Database statistics
GET  /api/db/tables                List all tables with row counts
GET  /api/db/table/{name}          Paginated table data
GET  /api/db/table/{name}/schema   Table column definitions
POST /api/db/query                 Run read-only SQL query
```

**Examples:**

```bash
curl http://localhost:8000/api/db/stats
curl http://localhost:8000/api/db/tables
curl http://localhost:8000/api/db/table/foods?page=1&per_page=20
curl http://localhost:8000/api/db/table/foods/schema

# Run SQL query
curl -X POST http://localhost:8000/api/db/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT food_id, name_en, name_ar FROM foods LIMIT 5"}'
```

---

### Cache Management

```
GET  /api/cache/stats              Cache hit rate and entry counts
POST /api/cache/invalidate         Clear all cached results
```

**Auth:** Invalidate requires `X-API-Key` header

**Examples:**

```bash
curl http://localhost:8000/api/cache/stats

curl -X POST http://localhost:8000/api/cache/invalidate \
  -H "X-API-Key: your-key"
```

---

### Scraper Control

```
GET  /api/scraper/status           Background scraper status
POST /api/scraper/start            Start background scraper
POST /api/scraper/stop             Stop background scraper
```

**Examples:**

```bash
curl http://localhost:8000/api/scraper/status
curl -X POST http://localhost:8000/api/scraper/start
curl -X POST http://localhost:8000/api/scraper/stop
```

---

### Worker Management (Coordinator Mode)

```
GET    /api/workers                       List all registered workers
POST   /api/workers/register              Register a worker
DELETE /api/workers/{name}                Deregister a worker
POST   /api/workers/{name}/heartbeat      Worker heartbeat
GET    /api/workers/{name}/status         Worker status
GET    /api/coordinator/health            Coordinator health check
GET    /api/worker/info                   Worker node info
```

**Examples:**

```bash
# List workers
curl http://localhost:8000/api/workers

# Register a worker
curl -X POST http://localhost:8000/api/workers/register \
  -H "Content-Type: application/json" \
  -d '{"name": "worker-laptop", "url": "https://device.ngrok.io"}'

# Coordinator health
curl http://localhost:8000/api/coordinator/health
```

---

### List AI Keys

```
GET /api/ai-keys
```

**Example:**

```bash
curl http://localhost:8000/api/ai-keys
```

---

## 3. Environment Variables

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
| `AI_PROVIDER_PRIORITY` | `openai,gemini,...` | AI provider priority (comma-separated) |
| `SCRAPER_TIMEOUT` | `30` | Web scraper timeout (seconds) |
| `BACKGROUND_SCRAPER_ENABLED` | `true` | Auto-start background scraper |
| `BACKGROUND_SCRAPER_BATCH_SIZE` | `10` | Foods per scraping batch |
| `BACKGROUND_SCRAPER_INTERVAL` | `300` | Seconds between scrape batches |
| `CACHE_TTL` | `3600` | Cache time-to-live (seconds) |
| `CACHE_MAX_MEMORY` | `1000` | Max in-memory cache entries |
| `NODE_MODE` | `standalone` | `standalone`, `coordinator`, or `worker` |
| `COORDINATOR_URL` | | Coordinator server ngrok URL (for workers) |
| `WORKER_NAME` | `worker-1` | Worker node name |
| `WORKER_NGROK_URL` | | This worker's ngrok URL |
| `HEALTH_CHECK_INTERVAL` | `15` | Seconds between health checks |
| `HEALTH_CHECK_TIMEOUT` | `5` | Health check timeout (seconds) |
| `HEALTH_CHECK_FAILURE_THRESHOLD` | `3` | Failures before marking worker inactive |
| `WORKER_HEARTBEAT_INTERVAL` | `30` | Seconds between worker heartbeats |

---

## 4. Multi-Device Setup

### Standalone Mode (default)

```bash
python main.py serve
```

Single server, all features local.

### Coordinator Mode

```bash
# .env
NODE_MODE=coordinator
```

```bash
python main.py serve
```

Manages workers, distributes search requests via round-robin, health checks workers.

### Worker Mode

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

Registers with coordinator, processes delegated search requests, sends heartbeats.

### Setup Steps

1. Start coordinator server, expose via ngrok
2. On each worker device, install dependencies and configure `.env`
3. Start worker servers, expose each via ngrok
4. Coordinator auto-registers workers and distributes load

---

## 5. Request/Response Examples

### Search Response (Found)

```json
{
  "success": true,
  "query": "banana",
  "lang": "en",
  "results": [
    {
      "food_id": "banana",
      "name_en": "Banana",
      "name_ar": "موزة",
      "carbs": 27.0,
      "category_en": "Fruits",
      "category_ar": "فواكه",
      "serving_description": "1 medium (118g)"
    }
  ],
  "message": "Found 1 result(s)"
}
```

### Search Response (Not Found)

```json
{
  "success": false,
  "query": "xyz",
  "lang": "en",
  "results": [],
  "message": "Sorry, no results found for 'xyz'"
}
```

### Arabic Search Response

```json
{
  "success": true,
  "query": "موزة",
  "lang": "ar",
  "results": [
    {
      "food_id": "banana",
      "name_en": "Banana",
      "name_ar": "موزة",
      "carbs": 27.0,
      "category_en": "Fruits",
      "category_ar": "فواكه",
      "serving_description": "1 medium (118g)"
    }
  ],
  "message": "تم العثور على نتيجة واحدة"
}
```

### Add Food Response

```json
{
  "success": true,
  "message": "Food 'Kiwi' added successfully"
}
```

### Bulk Add Response

```json
{
  "success": true,
  "added": 2,
  "skipped": 0,
  "total": 2
}
```

### Delete Food Response

```json
{
  "success": true,
  "message": "Food 'kiwi' deleted successfully"
}
```

### Cache Stats Response

```json
{
  "success": true,
  "cache": {
    "memory_entries": 42,
    "db_entries": 156,
    "total_queries": 1024,
    "cache_hits": 890,
    "hit_rate": 86.91
  }
}
```

### DB Stats Response

```json
{
  "success": true,
  "stats": {
    "tables": {
      "foods": 152,
      "aliases": 304,
      "nutrient_records": 152,
      "search_cache": 42
    },
    "db_size_bytes": 204800
  }
}
```

### Coordinator Health Response

```json
{
  "status": "healthy",
  "mode": "coordinator",
  "active_workers": 3,
  "total_workers": 3
}
```

### Auth Error Response

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "x-api-key"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

---

## Quick Reference

```
CLI:
  python main.py search -q "food"              Search food
  python main.py serve                          Start server
  python main.py generate-key -n "name"        Generate API key
  python main.py list-keys                      List all keys
  python main.py bulk-scrape -f foods.json      Bulk scrape from file
  python main.py bulk-scrape -t "a,b,c"         Bulk scrape from text
  python main.py scrape-single --name-en food   Scrape single food

API:
  GET  /api/foods/search?q=banana               Search (no auth)
  POST /api/foods/search                        Search POST (no auth)
  GET  /api/foods                               List all (no auth)
  POST /api/foods                               Add food (auth)
  POST /api/foods/bulk                          Bulk add (auth)
  DELETE /api/foods/{id}                        Delete food (auth)
  GET  /api/db/stats                            DB stats
  GET  /api/db/tables                           DB tables
  GET  /api/db/table/{name}                     Table data
  POST /api/db/query                            SQL query
  GET  /api/cache/stats                         Cache stats
  POST /api/cache/invalidate                    Clear cache (auth)
  GET  /api/scraper/status                      Scraper status
  POST /api/scraper/start                       Start scraper
  POST /api/scraper/stop                        Stop scraper
  GET  /api/workers                             List workers
  POST /api/workers/register                    Register worker
  GET  /api/coordinator/health                  Coordinator health
  GET  /api/worker/info                         Worker info
  POST /api/auth/key                            Generate key
  GET  /api/ai-keys                             AI provider keys
  GET  /api/health                              Health check

Web UI:
  http://localhost:8000/                         Dashboard
  http://localhost:8000/db                       Database viewer
  http://localhost:8000/docs                     API documentation

AUTH HEADER: X-API-Key: food_ai_XXXXXXXXXXXXXXXX
```
