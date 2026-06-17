from pydantic import BaseModel, Field
from typing import Optional


class Food(BaseModel):
    food_id: str
    name_en: str
    name_ar: str
    carbs: float = Field(..., ge=0, description="Carbs per serving in grams")
    category_en: str = ""
    category_ar: str = ""
    serving_description: str = ""


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
