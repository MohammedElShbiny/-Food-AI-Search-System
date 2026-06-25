from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class ScraperPauseMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, bg_scraper):
        super().__init__(app)
        self.scraper = bg_scraper

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        should_pause = (
            path == "/api/foods/search"
            and method in ("GET", "POST")
        )

        was_running = False
        if should_pause and self.scraper.running and not self.scraper.is_paused():
            was_running = True
            await self.scraper.pause()

        try:
            response = await call_next(request)
        finally:
            if was_running:
                await self.scraper.resume()

        return response
