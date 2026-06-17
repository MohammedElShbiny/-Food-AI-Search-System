# Food AI - Complete Commands Reference

## Table of Contents

1. [CLI Commands](#1-cli-commands)
2. [API Endpoints](#2-api-endpoints)
3. [Request/Response Examples](#3-requestresponse-examples)

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

**Example:**
```bash
python main.py serve --host 127.0.0.1 --port 3000
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
```

```bash
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
| `food_id` | Yes | Unique ID (e.g., "kiwi") |
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

## 3. Request/Response Examples

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

### Delete Food Response

```json
{
  "success": true,
  "message": "Food 'kiwi' deleted successfully"
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
  python main.py search -q "food"        Search food
  python main.py serve                    Start server
  python main.py generate-key -n "name"  Generate API key
  python main.py list-keys               List all keys

API:
  GET  /api/foods/search?q=banana        Search (no auth)
  POST /api/foods/search                 Search POST (no auth)
  GET  /api/foods                        List all (no auth)
  POST /api/foods                        Add food (auth required)
  DELETE /api/foods/{id}                 Delete food (auth required)
  POST /api/auth/key                     Generate key (no auth)
  GET  /api/health                       Health check (no auth)

AUTH HEADER: X-API-Key: food_ai_XXXXXXXXXXXXXXXX
```
