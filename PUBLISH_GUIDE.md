# Food AI API - Complete Publishing & Integration Guide

## Table of Contents

1. [Run Locally](#1-run-locally)
2. [Publish to Internet (Global)](#2-publish-to-internet)
3. [Integrate with Mobile App](#3-integrate-with-mobile-app)
4. [API Reference](#4-api-reference)

---

## 1. Run Locally

### Start the server

```bash
cd food_ai
pip install -r requirements.txt
python main.py serve
```

Server runs at: `http://localhost:8000`

### Test it

```
http://localhost:8000/api/foods/search?q=banana
http://localhost:8000/api/health
```

---

## 2. Publish to Internet

### Option A: Ngrok (Quickest - 2 minutes)

**Step 1:** Install ngrok

```bash
pip install pyngrok
```

**Step 2:** Start your server

```bash
python main.py serve
```

**Step 3:** Open new terminal, run ngrok

```bash
ngrok http 8000
```

**Step 4:** Copy the HTTPS URL

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

**Done!** Your API is now global at `https://abc123.ngrok-free.app`

---

### Option B: Railway (Free - Permanent)

**Step 1:** Create GitHub repository

```bash
cd food_ai
git init
git add .
git commit -m "Initial commit"
```

Go to github.com → New repository → Create

**Step 2:** Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/food-ai-api.git
git push -u origin main
```

**Step 3:** Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your `food-ai-api` repository
5. Railway will auto-detect Python

**Step 4:** Set environment variables
In Railway dashboard → Variables tab:

```
PORT=8000
PYTHON_VERSION=3.12
```

**Step 5:** Set start command
In Railway dashboard → Settings → Start Command:

```
cd food_ai && python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Step 6:** Get your URL
Railway gives you: `https://food-ai-api-production.up.railway.app`

---

### Option C: Render (Free - Permanent)

**Step 1:** Push code to GitHub (same as Railway Step 1-2)

**Step 2:** Deploy on Render

1. Go to [render.com](https://render.com)
2. Sign in with GitHub
3. Click **New** → **Web Service**
4. Connect your `food-ai-api` repository

**Step 3:** Configure

- **Name:** food-ai-api
- **Build Command:** `pip install -r food_ai/requirements.txt`
- **Start Command:** `cd food_ai && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`

**Step 4:** Deploy
Click **Create Web Service**

Get URL: `https://food-ai-api.onrender.com`

---

### Option D: Fly.io (Free tier)

```bash
# Install fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app
cd food_ai
fly launch

# Deploy
fly deploy
```

Get URL: `https://food-ai-api.fly.dev`

---

## 3. Integrate with Mobile App

### Step 1: Generate API Key

```bash
python main.py generate-key -n my-mobile-app
```

Save this key: `food_ai_XXXXXXXXXXXXXXXX`

### Step 2: Set API URL in Your App

Replace `localhost:8000` with your global URL:

```javascript
const API_URL = 'https://food-ai-api-production.up.railway.app';
const API_KEY = 'food_ai_XXXXXXXXXXXXXXXX';
```

---

### Integration Examples

#### React Native / Expo

```javascript
const API_URL = 'https://food-ai-api-production.up.railway.app';
const API_KEY = 'food_ai_XXXXXXXXXXXXXXXX';

// Search food (no auth needed)
async function searchFood(query) {
  const response = await fetch(
    `${API_URL}/api/foods/search?q=${encodeURIComponent(query)}`
  );
  return await response.json();
}

// Add food (auth required)
async function addFood(food) {
  const response = await fetch(`${API_URL}/api/foods`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify(food)
  });
  return await response.json();
}

// Usage
const results = await searchFood('banana');
console.log(results);
// { success: true, results: [{ name_en: "Banana", name_ar: "موزة", carbs: 27.0 }] }
```

#### Flutter / Dart

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

const API_URL = 'https://food-ai-api-production.up.railway.app';
const API_KEY = 'food_ai_XXXXXXXXXXXXXXXX';

// Search food
Future<Map<String, dynamic>> searchFood(String query) async {
  final response = await http.get(
    Uri.parse('$API_URL/api/foods/search?q=$query'),
  );
  return json.decode(response.body);
}

// Add food
Future<Map<String, dynamic>> addFood(Map<String, dynamic> food) async {
  final response = await http.post(
    Uri.parse('$API_URL/api/foods'),
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: json.encode(food),
  );
  return json.decode(response.body);
}

// Usage
final results = await searchFood('banana');
print(results);
```

#### Swift (iOS)

```swift
let API_URL = "https://food-ai-api-production.up.railway.app"
let API_KEY = "food_ai_XXXXXXXXXXXXXXXX"

// Search food
func searchFood(query: String, completion: @escaping ([String: Any]) -> Void) {
    let url = URL(string: "\(API_URL)/api/foods/search?q=\(query)")!
    URLSession.shared.dataTask(with: url) { data, response, error in
        guard let data = data,
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return }
        completion(json)
    }.resume()
}

// Add food
func addFood(food: [String: Any], completion: @escaping ([String: Any]) -> Void) {
    let url = URL(string: "\(API_URL)/api/foods")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.addValue("application/json", forHTTPHeaderField: "Content-Type")
    request.addValue(API_KEY, forHTTPHeaderField: "X-API-Key")
    request.httpBody = try? JSONSerialization.data(withJSONObject: food)
    URLSession.shared.dataTask(with: request) { data, response, error in
        guard let data = data,
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return }
        completion(json)
    }.resume()
}
```

#### Kotlin (Android)

```kotlin
import okhttp3.*
import org.json.JSONObject

val API_URL = "https://food-ai-api-production.up.railway.app"
val API_KEY = "food_ai_XXXXXXXXXXXXXXXX"
val client = OkHttpClient()

// Search food
fun searchFood(query: String): JSONObject {
    val request = Request.Builder()
        .url("$API_URL/api/foods/search?q=$query")
        .get()
        .build()
    val response = client.newCall(request).execute()
    return JSONObject(response.body?.string() ?: "{}")
}

// Add food
fun addFood(food: JSONObject): JSONObject {
    val body = RequestBody.create(
        MediaType.parse("application/json"),
        food.toString()
    )
    val request = Request.Builder()
        .url("$API_URL/api/foods")
        .post(body)
        .addHeader("Content-Type", "application/json")
        .addHeader("X-API-Key", API_KEY)
        .build()
    val response = client.newCall(request).execute()
    return JSONObject(response.body?.string() ?: "{}")
}
```

#### C# / Unity

```csharp
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;

const string API_URL = "https://food-ai-api-production.up.railway.app";
const string API_KEY = "food_ai_XXXXXXXXXXXXXXXX";

// Search food
IEnumerator SearchFood(string query, System.Action<string> callback) {
    using (UnityWebRequest request = UnityWebRequest.Get($"{API_URL}/api/foods/search?q={query}")) {
        yield return request.SendWebRequest();
        callback(request.downloadHandler.text);
    }
}

// Add food
IEnumerator AddFood(string json, System.Action<string> callback) {
    using (UnityWebRequest request = new UnityWebRequest($"{API_URL}/api/foods", "POST")) {
        byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(json);
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");
        request.SetRequestHeader("X-API-Key", API_KEY);
        yield return request.SendWebRequest();
        callback(request.downloadHandler.text);
    }
}

// Usage
StartCoroutine(SearchFood("banana", (result) => Debug.Log(result)));
```

---

## 4. API Reference

### Endpoints

| Method | URL | Auth | Body |
|--------|-----|------|------|
| GET | `/api/foods/search?q=banana` | No | - |
| POST | `/api/foods/search` | No | `{"query":"banana"}` |
| GET | `/api/foods` | No | - |
| POST | `/api/foods` | Yes | `{"food_id":"x","name_en":"X","name_ar":"X","carbs":0}` |
| DELETE | `/api/foods/{food_id}` | Yes | - |
| POST | `/api/auth/key` | No | `{"name":"my-app"}` |
| GET | `/api/health` | No | - |

### Response Format

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

### Not Found Response

```json
{
  "success": false,
  "query": "xyz",
  "lang": "en",
  "results": [],
  "message": "Sorry, no results found for 'xyz'"
}
```

### Arabic Search

Just type in Arabic:

```
GET /api/foods/search?q=موزة
```

Response:

```json
{
  "success": true,
  "query": "موزة",
  "lang": "ar",
  "results": [...],
  "message": "تم العثور على نتيجة واحدة"
}
```

---

## Quick Reference Card

```
LOCAL:     http://localhost:8000
NGROK:     https://abc123.ngrok-free.app
RAILWAY:   https://your-app.up.railway.app
RENDER:    https://your-app.onrender.com
FLY.IO:    https://your-app.fly.dev

AUTH HEADER: X-API-Key: food_ai_XXXXXXXXXXXXXXXX

SEARCH (no auth):  GET  /api/foods/search?q=banana
ADD (auth needed): POST /api/foods + body + X-API-Key header
DELETE (auth):     DELETE /api/foods/{id} + X-API-Key header
```
