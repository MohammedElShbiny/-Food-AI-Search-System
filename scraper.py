import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from models import Food
import config


def _generate_food_id(name_en: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name_en.lower().strip()).strip('_')


class FoodScraper:
    def __init__(self):
        self.timeout = config.SCRAPER_TIMEOUT
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=self.headers)

    async def close(self):
        await self.client.aclose()

    async def scrape_arabic(self, query: str) -> Food | None:
        for method in [self._scrape_webteb, self._scrape_mawdoo3, self._scrape_supermama]:
            try:
                result = await method(query)
                if result:
                    return result
            except Exception:
                continue
        return None

    async def scrape_english(self, query: str) -> Food | None:
        for method in [self._scrape_usda, self._scrape_openfoodfacts, self._scrape_healthline,
                       self._scrape_fatsecret, self._scrape_nutritionix]:
            try:
                result = await method(query)
                if result:
                    return result
            except Exception:
                continue
        return None

    async def scrape_all(self, query_en: str, query_ar: str = "") -> list[Food]:
        """Fan out to ALL sources concurrently. Returns all successful results."""
        tasks = []
        if query_ar:
            for method in [self._scrape_webteb, self._scrape_mawdoo3, self._scrape_supermama,
                           self._scrape_fatoora, self._scrape_akhbarak]:
                tasks.append(self._safe_scrape(method, query_ar))
        for method in [self._scrape_usda, self._scrape_openfoodfacts, self._scrape_healthline,
                       self._scrape_fatsecret, self._scrape_nutritionix]:
            tasks.append(self._safe_scrape(method, query_en))
        if config.EDAMAM_APP_ID and config.EDAMAM_APP_KEY:
            tasks.append(self._safe_scrape(self._scrape_edamam, query_en))
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    @staticmethod
    async def _safe_scrape(method, query: str) -> Food | None:
        try:
            return await method(query)
        except Exception:
            return None

    async def _scrape_webteb(self, query: str) -> Food | None:
        resp = await self.client.get(f"https://www.webteb.com/search?q={query}")
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        link = soup.select_one("a.search-result-link, a[href*='nutrition'], a[href*=' calorie']")
        if not link:
            return None
        href = link.get("href", "")
        if not href.startswith("http"):
            href = f"https://www.webteb.com{href}"
        resp2 = await self.client.get(href)
        if resp2.status_code != 200:
            return None
        page = BeautifulSoup(resp2.text, "lxml")
        return self._parse_webteb_page(page, query)

    def _parse_webteb_page(self, soup: BeautifulSoup, query: str) -> Food | None:
        text = soup.get_text(" ", strip=True)
        carbs = self._extract_number(text, r'(?:الكربوهيدات|الكرbohydrات|carbs?)\s*[:\s]*(\d+(?:\.\d+)?)')
        if carbs is None:
            return None
        name_en = query if not self._is_arabic(query) else query
        name_ar = query if self._is_arabic(query) else query
        return Food(
            food_id=_generate_food_id(query),
            name_en=name_en,
            name_ar=name_ar,
            carbs=carbs,
            serving_description="per 100g (webteb)",
            source="webteb",
        )

    async def _scrape_mawdoo3(self, query: str) -> Food | None:
        resp = await self.client.get(f"https://www.mawdoo3.com/search?q={query}")
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        link = soup.select_one("a.search-result, a[href*='تغذية'], a[href*='سعرات']")
        if not link:
            return None
        href = link.get("href", "")
        if not href.startswith("http"):
            href = f"https://www.mawdoo3.com{href}"
        resp2 = await self.client.get(href)
        if resp2.status_code != 200:
            return None
        page = BeautifulSoup(resp2.text, "lxml")
        return self._parse_mawdoo3_page(page, query)

    def _parse_mawdoo3_page(self, soup: BeautifulSoup, query: str) -> Food | None:
        text = soup.get_text(" ", strip=True)
        carbs = self._extract_number(text, r'(?:الكربوهيدات|carbs?)\s*[:\s]*(\d+(?:\.\d+)?)')
        if carbs is None:
            return None
        name_en = query if not self._is_arabic(query) else query
        name_ar = query if self._is_arabic(query) else query
        return Food(
            food_id=_generate_food_id(query),
            name_en=name_en,
            name_ar=name_ar,
            carbs=carbs,
            serving_description="per 100g (mawdoo3)",
            source="mawdoo3",
        )

    async def _scrape_supermama(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            resp = await client.get(f"https://www.supermama.me/search?q={query}")
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            link = soup.select_one("a.post-link, a[href*=' nutrition'], a[href*='وصفة']")
            if not link:
                return None
            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"https://www.supermama.me{href}"
            resp2 = await client.get(href)
            if resp2.status_code != 200:
                return None
            page = BeautifulSoup(resp2.text, "lxml")
            return self._parse_supermama_page(page, query)

    def _parse_supermama_page(self, soup: BeautifulSoup, query: str) -> Food | None:
        text = soup.get_text(" ", strip=True)
        carbs = self._extract_number(text, r'(?:الكربوهيدات|carbs?)\s*[:\s]*(\d+(?:\.\d+)?)')
        if carbs is None:
            return None
        name_en = query if not self._is_arabic(query) else query
        name_ar = query if self._is_arabic(query) else query
        return Food(
            food_id=_generate_food_id(query),
            name_en=name_en,
            name_ar=name_ar,
            carbs=carbs,
            serving_description="per 100g (supermama)",
            source="supermama",
        )

    async def _scrape_usda(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                "https://api.nal.usda.gov/fdc/v1/foods/search",
                params={"query": query, "pageSize": 1, "api_key": "DEMO_KEY"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            foods = data.get("foods", [])
            if not foods:
                return None
            item = foods[0]
            description = item.get("description", query)
            nutrients = {n["nutrientName"]: n["value"] for n in item.get("foodNutrients", [])}
            carbs = nutrients.get("Carbohydrate, by difference")
            if carbs is None:
                return None
            serving_g = 100
            for nutrient in item.get("foodNutrients", []):
                if nutrient.get("nutrientName") == "Energy":
                    break
            return Food(
                food_id=_generate_food_id(description),
                name_en=description,
                name_ar=query if self._is_arabic(query) else description,
                carbs=round(carbs * serving_g / 100, 1) if serving_g != 100 else carbs,
                category_en="USDA",
                serving_description=f"per 100g",
                source="usda",
            )

    async def _scrape_healthline(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            resp = await client.get(f"https://www.healthline.com/nutrition/{query.lower().replace(' ', '-')}-nutrition")
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(" ", strip=True)
            carbs = self._extract_number(text, r'(?:Carbs?|carbohydrates?)\s*[:\s]*(\d+(?:\.\d+)?)\s*g')
            if carbs is None:
                return None
            name_en = query if not self._is_arabic(query) else query
            name_ar = query if self._is_arabic(query) else query
            return Food(
                food_id=_generate_food_id(query),
                name_en=name_en,
                name_ar=name_ar,
                carbs=carbs,
                serving_description="per 100g (healthline)",
                source="healthline",
            )

    async def _scrape_nutritionix(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            resp = await client.post(
                "https://trackapi.nutritionix.com/v2/natural/nutrients",
                headers={"Content-Type": "application/json"},
                json={"query": query},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            foods = data.get("foods", [])
            if not foods:
                return None
            item = foods[0]
            carbs = item.get("nf_total_carbohydrate")
            if carbs is None:
                return None
            name_en = item.get("food_name", query)
            serving = item.get("serving_unit", "serving")
            serving_qty = item.get("serving_qty", 1)
            return Food(
                food_id=_generate_food_id(name_en),
                name_en=name_en,
                name_ar=query if self._is_arabic(query) else name_en,
                carbs=round(carbs, 1),
                serving_description=f"{serving_qty} {serving}",
                source="nutritionix",
            )

    async def _scrape_openfoodfacts(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                "https://world.openfoodfacts.org/cgi/search.pl",
                params={"search_terms": query, "json": 1, "page_size": 5},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            products = data.get("products", [])
            if not products:
                return None
            product = products[0]
            nutriments = product.get("nutriments", {})
            carbs = nutriments.get("carbohydrates_100g")
            if carbs is None:
                return None
            name = product.get("product_name", query)
            return Food(
                food_id=_generate_food_id(name),
                name_en=name if not self._is_arabic(query) else query,
                name_ar=query if self._is_arabic(query) else name,
                carbs=round(float(carbs), 1),
                serving_description="per 100g",
                source="openfoodfacts",
            )

    async def _scrape_edamam(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                "https://api.edamam.com/api/food-database/v2/parser",
                params={
                    "ingr": query,
                    "app_id": config.EDAMAM_APP_ID,
                    "app_key": config.EDAMAM_APP_KEY,
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            hints = data.get("hints", [])
            if not hints:
                return None
            food_data = hints[0].get("food", {})
            nutrients = food_data.get("nutrients", {})
            carbs = nutrients.get("CHOCDF")
            if carbs is None:
                return None
            name = food_data.get("label", query)
            return Food(
                food_id=_generate_food_id(name),
                name_en=name if not self._is_arabic(query) else query,
                name_ar=query if self._is_arabic(query) else name,
                carbs=round(float(carbs), 1),
                serving_description="per 100g",
                source="edamam",
            )

    async def _scrape_fatoora(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            resp = await client.get(f"https://fatoora.co/search?q={query}")
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            link = soup.select_one("a[href*='food'], a[href*='product'], a.search-result")
            if not link:
                return None
            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"https://fatoora.co{href}"
            resp2 = await client.get(href)
            if resp2.status_code != 200:
                return None
            text = BeautifulSoup(resp2.text, "lxml").get_text(" ", strip=True)
            carbs = self._extract_arabic_carbs(text, "fatoora")
            if carbs is None:
                return None
            return Food(
                food_id=_generate_food_id(query),
                name_en=query if not self._is_arabic(query) else query,
                name_ar=query if self._is_arabic(query) else query,
                carbs=carbs,
                serving_description="per 100g (fatoora)",
                source="fatoora",
            )

    async def _scrape_akhbarak(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            resp = await client.get(f"https://www.akhbarak.net/search?q={query}")
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            link = soup.select_one("a[href*='nutrition'], a[href*='سعرات'], a[href*='تغذية']")
            if not link:
                return None
            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"https://www.akhbarak.net{href}"
            resp2 = await client.get(href)
            if resp2.status_code != 200:
                return None
            text = BeautifulSoup(resp2.text, "lxml").get_text(" ", strip=True)
            carbs = self._extract_arabic_carbs(text, "akhbarak")
            if carbs is None:
                return None
            return Food(
                food_id=_generate_food_id(query),
                name_en=query if not self._is_arabic(query) else query,
                name_ar=query if self._is_arabic(query) else query,
                carbs=carbs,
                serving_description="per 100g (akhbarak)",
                source="akhbarak",
            )

    async def _scrape_fatsecret(self, query: str) -> Food | None:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            resp = await client.get(
                f"https://www.fatsecret.com/calories-nutrition/search?q={query}"
            )
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
            link = soup.select_one("a[href*='/calories-nutrition/']")
            if not link:
                return None
            href = link.get("href", "")
            if not href.startswith("http"):
                href = f"https://www.fatsecret.com{href}"
            resp2 = await client.get(href)
            if resp2.status_code != 200:
                return None
            text = BeautifulSoup(resp2.text, "lxml").get_text(" ", strip=True)
            carbs = self._extract_number(
                text, r'(?:Carbs?|carbohydrates?)\s*[:\s]*(\d+(?:\.\d+)?)\s*g'
            )
            if carbs is None:
                return None
            return Food(
                food_id=_generate_food_id(query),
                name_en=query if not self._is_arabic(query) else query,
                name_ar=query if self._is_arabic(query) else query,
                carbs=carbs,
                serving_description="per 100g (fatsecret)",
                source="fatsecret",
            )

    @staticmethod
    def _extract_arabic_carbs(text: str, source_name: str) -> float | None:
        match = re.search(
            r'(?:الكربوهيدات|الكرbohydrات|carbs?)\s*[:\s]*(\d+(?:\.\d+)?)',
            text, re.IGNORECASE
        )
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def _extract_number(text: str, pattern: str) -> float | None:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def _is_arabic(text: str) -> bool:
        return bool(re.search(r'[\u0600-\u06FF]', text))
