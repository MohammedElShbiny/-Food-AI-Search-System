import asyncio
import json
import time
import os
from datetime import datetime
import click
from scraper import FoodScraper, _generate_food_id
from database import get_database
from models import Food
import config


SOURCE_PRIORITY = ["usda", "openfoodfacts", "edamam", "healthline", "fatsecret",
                   "webteb", "mawdoo3", "supermama", "fatoora", "akhbarak", "nutritionix"]


class BulkScraper:
    def __init__(self, max_concurrent: int = None, delay: float = None):
        self.max_concurrent = max_concurrent or config.BULK_SCRAPER_CONCURRENCY
        self.delay = delay if delay is not None else config.BULK_SCRAPER_DELAY
        self.scraper = FoodScraper()
        self.db = get_database()
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    def select_best_result(self, results: list[Food]) -> Food | None:
        valid = [r for r in results if isinstance(r, Food) and r.carbs > 0]
        if not valid:
            return None
        for src in SOURCE_PRIORITY:
            match = [r for r in valid if r.source == src]
            if match:
                return match[0]
        return valid[0]

    async def scrape_food(self, name_en: str, name_ar: str = "") -> dict:
        start = time.time()
        try:
            results = await self.scraper.scrape_all(name_en, name_ar)
        except Exception:
            results = []
        elapsed = round(time.time() - start, 2)
        best = self.select_best_result(results)
        return {
            "name_en": name_en,
            "name_ar": name_ar,
            "carbs": best.carbs if best else None,
            "source": best.source if best else None,
            "sources_tried": len(results),
            "sources_succeeded": sum(1 for r in results if r.carbs > 0),
            "duration": elapsed,
        }

    async def bulk_scrape(self, items: list[dict], dry_run: bool = False,
                          output_file: str = None) -> dict:
        results = {"success": 0, "failed": 0, "skipped": 0, "details": []}
        total = len(items)
        start_time = time.time()

        for i, item in enumerate(items):
            name_en = item.get("name_en", "")
            name_ar = item.get("name_ar", "")
            if not name_en:
                results["skipped"] += 1
                continue

            click.echo(f"\r  [{i+1}/{total}] Scraping: {name_en}...", nl=False)

            async with self.semaphore:
                if self.delay > 0:
                    await asyncio.sleep(self.delay)
                result = await self.scrape_food(name_en, name_ar)

            if result["carbs"] is not None:
                results["success"] += 1
                if not dry_run:
                    food = Food(
                        food_id=_generate_food_id(name_en),
                        name_en=name_en,
                        name_ar=name_ar,
                        carbs=result["carbs"],
                        category_en=item.get("category_en", ""),
                        category_ar=item.get("category_ar", ""),
                        serving_description=f"per 100g ({result['source']})",
                        source=result["source"],
                    )
                    self.db.add_food(food)
                status = "OK"
            else:
                results["failed"] += 1
                status = "FAIL"

            result["status"] = status
            results["details"].append(result)
            click.echo(f"\r  [{i+1}/{total}] {name_en}: {status}"
                       f"  (carbs={result['carbs']}, source={result['source']})")

        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        results["duration"] = f"{minutes}m {seconds}s"
        results["total"] = total

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            click.echo(f"\n  Report saved to {output_file}")

        return results


class BackgroundScraper:
    def __init__(self):
        self.running = False
        self.task = None
        self.status = {
            "state": "idle",
            "current_food": None,
            "foods_scraped": 0,
            "foods_failed": 0,
            "total_foods": 0,
            "batch_number": 0,
            "last_batch_time": None,
            "errors": [],
            "started_at": None,
        }
        self.scraper = FoodScraper()
        self.db = get_database()
        self._stop_event = asyncio.Event()
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()

    async def start(self):
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self.status["state"] = "running"
        self.status["started_at"] = datetime.now().isoformat()
        self.task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self.running = False
        self._stop_event.set()
        self.status["state"] = "stopped"
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def pause(self):
        if self.running and not self._paused:
            self._paused = True
            self._pause_event.clear()

    async def resume(self):
        if self._paused:
            self._paused = False
            self._pause_event.set()

    def is_paused(self):
        return self._paused

    async def _run_loop(self):
        food_list_path = os.path.join(os.path.dirname(__file__), "food_list.json")
        if not os.path.exists(food_list_path):
            self.status["state"] = "error"
            self.status["errors"].append({"error": f"food_list.json not found"})
            return

        foods = load_food_list(food_list_path)
        interval = config.BACKGROUND_SCRAPER_INTERVAL

        while self.running:
            self.status["batch_number"] += 1
            self.status["total_foods"] = len(foods)

            batch_size = config.BACKGROUND_SCRAPER_BATCH_SIZE
            for i in range(0, len(foods), batch_size):
                if not self.running:
                    break
                if self._paused:
                    await self._pause_event.wait()
                    if not self.running:
                        break
                batch = foods[i:i + batch_size]
                await self._scrape_batch(batch)

            self.status["last_batch_time"] = datetime.now().isoformat()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass

    async def _scrape_batch(self, batch):
        tasks = [self._scrape_one(item) for item in batch]
        await asyncio.gather(*tasks)

    async def _scrape_one(self, item):
        name_en = item.get("name_en", "")
        name_ar = item.get("name_ar", "")
        self.status["current_food"] = name_en
        try:
            results = await self.scraper.scrape_all(name_en, name_ar)
            valid = [r for r in results if isinstance(r, Food) and r.carbs > 0]
            best = None
            if valid:
                for src in SOURCE_PRIORITY:
                    match = [r for r in valid if r.source == src]
                    if match:
                        best = match[0]
                        break
                if not best:
                    best = valid[0]
            if best:
                food = Food(
                    food_id=_generate_food_id(name_en),
                    name_en=name_en,
                    name_ar=name_ar,
                    carbs=best.carbs,
                    category_en=item.get("category_en", ""),
                    category_ar=item.get("category_ar", ""),
                    serving_description=f"per 100g ({best.source})",
                    source=best.source,
                )
                self.db.add_food(food)
                self.status["foods_scraped"] += 1
            else:
                self.status["foods_failed"] += 1
        except Exception as e:
            self.status["foods_failed"] += 1
            self.status["errors"].append({"food": name_en, "error": str(e)})
        self.status["current_food"] = None

    def get_status(self):
        return dict(self.status)


def load_food_list(file_path: str) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_text_items(text: str) -> list[dict]:
    items = []
    for item in text.split(","):
        item = item.strip()
        if item:
            items.append({"name_en": item, "name_ar": ""})
    return items


@click.command()
@click.option("--file", "-f", "food_file", type=click.Path(exists=True),
              help="JSON file with food list")
@click.option("--text", "-t", "food_text",
              help="Comma-separated food items")
@click.option("--concurrency", "-c", default=config.BULK_SCRAPER_CONCURRENCY,
              help="Max concurrent scraping tasks")
@click.option("--delay", "-d", default=config.BULK_SCRAPER_DELAY,
              help="Delay between requests in seconds")
@click.option("--output", "-o", "output_file", type=click.Path(),
              help="Save results report to JSON file")
@click.option("--dry-run", is_flag=True, help="Don't write to database")
def bulk_scrape(food_file, food_text, concurrency, delay, output_file, dry_run):
    """Bulk scrape carb data from multiple food websites."""
    if not food_file and not food_text:
        click.echo("Error: Provide --file or --text")
        return

    if food_file:
        items = load_food_list(food_file)
    else:
        items = parse_text_items(food_text)

    click.echo(f"\nBulk Scraping: {len(items)} foods from all sources")
    click.echo(f"  Concurrency: {concurrency}, Delay: {delay}s")
    if dry_run:
        click.echo("  Mode: DRY RUN (no DB writes)")
    click.echo()

    scraper = BulkScraper(max_concurrent=concurrency, delay=delay)
    results = asyncio.run(scraper.bulk_scrape(items, dry_run=dry_run,
                                               output_file=output_file))

    click.echo(f"\n{'='*50}")
    click.echo(f"  Total: {results['total']}")
    click.echo(f"  Success: {results['success']}")
    click.echo(f"  Failed: {results['failed']}")
    click.echo(f"  Skipped: {results['skipped']}")
    click.echo(f"  Duration: {results['duration']}")
    click.echo()


@click.command()
@click.option("--name-en", required=True, help="English food name")
@click.option("--name-ar", default="", help="Arabic food name")
def scrape_single(name_en, name_ar):
    """Scrape one food item from all sources."""
    click.echo(f"\nScraping: {name_en} ({name_ar}) from all sources...\n")

    scraper = BulkScraper(max_concurrent=1, delay=0)
    result = asyncio.run(scraper.scrape_food(name_en, name_ar))

    if result["carbs"] is not None:
        click.echo(f"  Best result: {result['carbs']}g carbs ({result['source']})")
    else:
        click.echo("  No results found from any source")

    click.echo(f"  Sources tried: {result['sources_tried']}")
    click.echo(f"  Sources succeeded: {result['sources_succeeded']}")
    click.echo(f"  Duration: {result['duration']}s")
    click.echo()
