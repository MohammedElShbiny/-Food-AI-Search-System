import asyncio
import time
import httpx
from datetime import datetime
import config


class Coordinator:
    def __init__(self):
        self.workers: dict[str, dict] = {}
        self._round_robin_index = 0
        self._health_check_task = None

    def register_worker(self, name: str, url: str) -> dict:
        self.workers[name] = {
            "name": name,
            "url": url,
            "status": "active",
            "last_heartbeat": datetime.now().isoformat(),
            "current_load": 0,
            "failures": 0,
            "registered_at": datetime.now().isoformat(),
        }
        return self.workers[name]

    def deregister_worker(self, name: str) -> bool:
        if name in self.workers:
            del self.workers[name]
            return True
        return False

    def worker_heartbeat(self, name: str, url: str = None) -> bool:
        if name not in self.workers:
            return False
        self.workers[name]["last_heartbeat"] = datetime.now().isoformat()
        self.workers[name]["status"] = "active"
        self.workers[name]["failures"] = 0
        if url:
            self.workers[name]["url"] = url
        return True

    def get_active_workers(self) -> list[dict]:
        return [w for w in self.workers.values() if w["status"] == "active"]

    def get_next_worker(self) -> dict | None:
        active = self.get_active_workers()
        if not active:
            return None
        worker = active[self._round_robin_index % len(active)]
        self._round_robin_index += 1
        return worker

    async def proxy_request(self, method: str, path: str, json_data=None) -> dict | None:
        worker = self.get_next_worker()
        if not worker:
            return None
        timeout = config.HEALTH_CHECK_TIMEOUT
        async with httpx.AsyncClient(timeout=timeout * 3) as client:
            try:
                url = f"{worker['url']}{path}"
                if method == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.post(url, json=json_data)
                if resp.status_code == 200:
                    worker["current_load"] = max(0, worker.get("current_load", 0) - 1)
                    return resp.json()
            except Exception:
                worker["failures"] = worker.get("failures", 0) + 1
                if worker["failures"] >= config.HEALTH_CHECK_FAILURE_THRESHOLD:
                    worker["status"] = "inactive"
        return None

    async def health_check_loop(self):
        while True:
            await asyncio.sleep(config.HEALTH_CHECK_INTERVAL)
            for name, worker in list(self.workers.items()):
                if worker["status"] != "active":
                    continue
                async with httpx.AsyncClient(timeout=config.HEALTH_CHECK_TIMEOUT) as client:
                    try:
                        resp = await client.get(f"{worker['url']}/api/health")
                        if resp.status_code == 200:
                            worker["failures"] = 0
                        else:
                            worker["failures"] = worker.get("failures", 0) + 1
                    except Exception:
                        worker["failures"] = worker.get("failures", 0) + 1

                if worker["failures"] >= config.HEALTH_CHECK_FAILURE_THRESHOLD:
                    worker["status"] = "inactive"

    async def start_health_checks(self):
        self._health_check_task = asyncio.create_task(self.health_check_loop())

    async def stop(self):
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    def get_all_workers(self) -> list[dict]:
        return list(self.workers.values())

    def get_worker_status(self, name: str) -> dict | None:
        return self.workers.get(name)
