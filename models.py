from pydantic import BaseModel, Field
from typing import Optional


class Food(BaseModel):
    food_id: Optional[str] = None
    name_en: str
    name_ar: str
    carbs: float = Field(..., ge=0, description="Carbs per serving in grams")
    category_en: str = ""
    category_ar: str = ""
    serving_description: str = ""
    source: str = "database"


class FoodResponse(BaseModel):
    success: bool
    query: str
    lang: str
    results: list[Food]
    message: str


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, description="API key name/label")


class APIKey(BaseModel):
    key: str
    name: str
    created_at: str
    is_active: bool = True


class WorkerRegistration(BaseModel):
    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)


class WorkerInfo(BaseModel):
    worker_id: str
    name: str
    url: str
    status: str = "active"
    last_heartbeat: Optional[str] = None
    current_load: int = 0


class DBQueryRequest(BaseModel):
    sql: str = Field(..., min_length=1)


class CacheStats(BaseModel):
    memory_entries: int
    total_queries: int
    cache_hits: int
    hit_rate: float
