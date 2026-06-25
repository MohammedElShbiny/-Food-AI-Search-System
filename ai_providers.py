import re
import json
import httpx
from abc import ABC, abstractmethod
from models import Food
import config


FOOD_SEARCH_PROMPT = """You are a food nutrition assistant. The user searched for a food item.

Search query: "{query}"
Language detected: {lang}

Return ONLY a JSON object (no markdown, no code fences) with these fields:
{{
  "food_id": "lowercase_snake_case_id",
  "name_en": "English food name",
  "name_ar": "Arabic food name",
  "carbs": 0.0,
  "category_en": "Category in English",
  "category_ar": "Category in Arabic",
  "serving_description": "e.g. per 100g or 1 medium (118g)"
}}

If you don't know the food or its carbs, return: {{"error": "not_found"}}"""


def _generate_food_id(name_en: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name_en.lower().strip()).strip('_')


class AIProvider(ABC):
    @abstractmethod
    async def search(self, query: str, lang: str) -> Food | None:
        pass

    def _parse_response(self, text: str) -> Food | None:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
            text = text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{[^{}]*"carbs"[^{}]*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                return None
        if "error" in data:
            return None
        if "carbs" not in data:
            return None
        return Food(
            food_id=data.get("food_id", _generate_food_id(data.get("name_en", "unknown"))),
            name_en=data.get("name_en", "Unknown"),
            name_ar=data.get("name_ar", "غير معروف"),
            carbs=float(data["carbs"]),
            category_en=data.get("category_en", ""),
            category_ar=data.get("category_ar", ""),
            serving_description=data.get("serving_description", "per 100g"),
            source=f"ai_{self.__class__.__name__.lower().replace('provider', '')}",
        )


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY

    async def search(self, query: str, lang: str) -> Food | None:
        if not self.api_key:
            return None
        prompt = FOOD_SEARCH_PROMPT.format(query=query, lang=lang)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0},
            )
            if resp.status_code != 200:
                return None
            text = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(text)


class GeminiProvider(AIProvider):
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY

    async def search(self, query: str, lang: str) -> Food | None:
        if not self.api_key:
            return None
        prompt = FOOD_SEARCH_PROMPT.format(query=query, lang=lang)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_response(text)


class ClaudeProvider(AIProvider):
    def __init__(self):
        self.api_key = config.CLAUDE_API_KEY

    async def search(self, query: str, lang: str) -> Food | None:
        if not self.api_key:
            return None
        prompt = FOOD_SEARCH_PROMPT.format(query=query, lang=lang)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            text = data["content"][0]["text"]
            return self._parse_response(text)


class OpenRouterProvider(AIProvider):
    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY

    async def search(self, query: str, lang: str) -> Food | None:
        if not self.api_key:
            return None
        prompt = FOOD_SEARCH_PROMPT.format(query=query, lang=lang)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code != 200:
                return None
            text = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(text)


class DeepSeekProvider(AIProvider):
    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY

    async def search(self, query: str, lang: str) -> Food | None:
        if not self.api_key:
            return None
        prompt = FOOD_SEARCH_PROMPT.format(query=query, lang=lang)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]},
            )
            if resp.status_code != 200:
                return None
            text = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(text)


class NVIDIAProvider(AIProvider):
    def __init__(self):
        self.api_key = config.NVIDIA_API_KEY

    async def search(self, query: str, lang: str) -> Food | None:
        if not self.api_key:
            return None
        prompt = FOOD_SEARCH_PROMPT.format(query=query, lang=lang)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": "meta/llama-3.1-8b-instruct", "messages": [{"role": "user", "content": prompt}]},
            )
            if resp.status_code != 200:
                return None
            text = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(text)


class AIFallback:
    PROVIDERS = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "claude": ClaudeProvider,
        "openrouter": OpenRouterProvider,
        "deepseek": DeepSeekProvider,
        "nvidia": NVIDIAProvider,
    }

    def __init__(self):
        self.providers = []
        for name in config.AI_PROVIDER_PRIORITY:
            name = name.strip()
            if name in self.PROVIDERS:
                provider = self.PROVIDERS[name]()
                self.providers.append(provider)

    async def search(self, query: str, lang: str) -> Food | None:
        for provider in self.providers:
            try:
                result = await provider.search(query, lang)
                if result:
                    return result
            except Exception:
                continue
        return None

    def get_configured_providers(self) -> list[str]:
        configured = []
        for name in config.AI_PROVIDER_PRIORITY:
            name = name.strip()
            cls = self.PROVIDERS.get(name)
            if cls:
                instance = cls()
                if instance.api_key:
                    configured.append(name)
        return configured
