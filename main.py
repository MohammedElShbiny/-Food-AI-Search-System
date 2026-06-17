import re
import uvicorn
import click
from fastapi import FastAPI, Query, Depends, HTTPException, Header
from models import Food, FoodResponse, APIKeyCreate
from api import APIKeyManager
from database import get_database
import config

app = FastAPI(
    title="Food AI Search API",
    description="AI-powered food database search with Arabic support",
    version="2.0.0",
)

key_manager = APIKeyManager()


def is_arabic(query: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', query))


async def verify_api_key(x_api_key: str = Header(...)):
    if not key_manager.validate_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return x_api_key


@app.get("/api/foods/search")
async def search_foods_get(q: str = Query(..., min_length=1)):
    db = get_database()
    results = db.search(q)
    lang = "ar" if is_arabic(q) else "en"
    if results:
        msg = f"تم العثور على {len(results)} نتيجة" if lang == "ar" else f"Found {len(results)} result(s)"
        return FoodResponse(success=True, query=q, lang=lang, results=results, message=msg)
    msg = f"عذراً، لم يتم العثور على نتائج لـ '{q}'" if lang == "ar" else f"Sorry, no results found for '{q}'"
    return FoodResponse(success=False, query=q, lang=lang, results=[], message=msg)


@app.post("/api/foods/search")
async def search_foods_post(body: dict):
    query = body.get("query", "")
    lang_param = body.get("lang", "auto")
    if not query:
        raise HTTPException(status_code=400, detail="Query field is required")
    db = get_database()
    results = db.search(query)
    lang = "ar" if is_arabic(query) else "en"
    if lang_param in ("en", "ar"):
        lang = lang_param
        results = db._search_by_lang(query, lang)
    if results:
        msg = f"تم العثور على {len(results)} نتيجة" if lang == "ar" else f"Found {len(results)} result(s)"
        return FoodResponse(success=True, query=query, lang=lang, results=results, message=msg)
    msg = f"عذراً، لم يتم العثور على نتائج لـ '{query}'" if lang == "ar" else f"Sorry, no results found for '{query}'"
    return FoodResponse(success=False, query=query, lang=lang, results=[], message=msg)


@app.get("/api/foods")
async def list_foods():
    db = get_database()
    foods = db.get_all()
    return {"success": True, "count": len(foods), "foods": foods}


@app.post("/api/foods")
async def add_food(food: Food, api_key: str = Depends(verify_api_key)):
    db = get_database()
    if db.add_food(food):
        return {"success": True, "message": f"Food '{food.name_en}' added successfully"}
    raise HTTPException(status_code=409, detail=f"Food '{food.food_id}' already exists")


@app.delete("/api/foods/{food_id}")
async def delete_food(food_id: str, api_key: str = Depends(verify_api_key)):
    db = get_database()
    if db.delete_food(food_id):
        return {"success": True, "message": f"Food '{food_id}' deleted successfully"}
    raise HTTPException(status_code=404, detail=f"Food '{food_id}' not found")


@app.post("/api/auth/key")
async def generate_api_key(body: APIKeyCreate):
    api_key = key_manager.generate_key(body.name)
    return {
        "success": True,
        "message": "API key generated. Save it - it won't be shown again!",
        "key": api_key.key,
        "name": api_key.name,
        "created_at": api_key.created_at,
    }


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Food AI Search API", "version": "2.0.0"}


@click.group()
def cli():
    pass


@cli.command()
@click.option("--query", "-q", required=True, help="Food name to search (English or Arabic)")
def search_cmd(query):
    db = get_database()
    results = db.search(query)
    lang = "ar" if is_arabic(query) else "en"
    if results:
        label = "نتيجة" if lang == "ar" else "result(s)"
        print(f"\n{'تم العثور على' if lang == 'ar' else 'Found'} {len(results)} {label} for '{query}':\n")
        for food in results:
            name = food.name_ar if lang == "ar" else food.name_en
            other = food.name_en if lang == "ar" else food.name_ar
            cat = food.category_ar if lang == "ar" else food.category_en
            print(f"  {name} ({other})")
            print(f"    {'الكرbohydrات' if lang == 'ar' else 'Carbs'}:    {food.carbs}g")
            if cat:
                print(f"    {'الفئة' if lang == 'ar' else 'Category'}: {cat}")
            if food.serving_description:
                print(f"    {'الحصة' if lang == 'ar' else 'Serving'}:  {food.serving_description}")
            print()
    else:
        print(f"\n{'عذراً، لم يتم العثور على نتائج' if lang == 'ar' else 'Sorry, no results found'} for '{query}'\n")


@cli.command()
@click.option("--host", default=config.HOST, help="Host to bind")
@click.option("--port", default=config.PORT, type=int, help="Port to bind")
def serve(host, port):
    print(f"Starting Food AI API on http://{host}:{port}")
    print(f"Database: {config.SQLITE_PATH}")
    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.option("--name", "-n", required=True, help="API key name/label")
def generate_key(name):
    api_key = key_manager.generate_key(name)
    print(f"\nAPI Key Generated:")
    print(f"  Name: {api_key.name}")
    print(f"  Key:  {api_key.key}")
    print(f"  Created: {api_key.created_at}")
    print(f"\nSave this key - it won't be shown again!\n")


@cli.command()
def list_keys():
    keys = key_manager.list_keys()
    if keys:
        print("\nAPI Keys:\n")
        for k in keys:
            status = "active" if k.is_active else "revoked"
            print(f"  {k.name}: {k.key[:20]}... ({status})")
    else:
        print("\nNo API keys found.\n")


cli.add_command(search_cmd, "search")


if __name__ == "__main__":
    cli()
