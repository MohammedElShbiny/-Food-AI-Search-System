import re
from models import Food
from scraper import FoodScraper
from ai_providers import AIFallback


def _is_arabic(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text))


class FallbackSearch:
    def __init__(self):
        self.scraper = FoodScraper()
        self.ai = AIFallback()

    async def search(self, query: str) -> Food | None:
        lang = "ar" if _is_arabic(query) else "en"

        if lang == "ar":
            result = await self.scraper.scrape_arabic(query)
            if result:
                return result
            result = await self.scraper.scrape_english(query)
            if result:
                return result
        else:
            result = await self.scraper.scrape_english(query)
            if result:
                return result
            result = await self.scraper.scrape_arabic(query)
            if result:
                return result

        result = await self.ai.search(query, lang)
        return result
