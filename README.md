# Food AI Search System

AI-powered food database search with Arabic + English support.

## Features

- 152 foods from Egyptian/Middle Eastern cuisine
- Arabic and English search (auto-detected)
- Bilingual display (name_en + name_ar)
- API key authentication
- REST API (GET/POST)
- CLI interface

## Setup

```bash
pip install -r requirements.txt
```

## CLI Usage

```bash
# Search in English
python main.py search -q banana

# Search in Arabic
python main.py search -q موز

# Start API server
python main.py serve

# Generate API key
python main.py generate-key -n my-app

# List API keys
python main.py list-keys
```

## API Endpoints

### Search (GET)

```bash
curl "http://localhost:8000/api/foods/search?q=banana"
curl "http://localhost:8000/api/foods/search?q=موز"
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

### Add Food (requires API key)

```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"food_id":"kiwi","name_en":"Kiwi","name_ar":"كيوي","carbs":15,"category_en":"Fruits","category_ar":"فواكه"}' \
  http://localhost:8000/api/foods
```

### Delete Food (requires API key)

```bash
curl -X DELETE -H "X-API-Key: your-key" http://localhost:8000/api/foods/kiwi
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
