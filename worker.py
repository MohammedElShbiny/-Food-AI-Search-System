import asyncio
import httpx
from datetime import datetime
import config


class WorkerNode:
    def __init__(self):
        self.name = config.WORKER_NAME
        self.ngrok_url = config.WORKER_NGROK_URL
        self.coordinator_url = config.COORDINATOR_URL
        self._heartbeat_task = None
        self.registered = False

    async def register(self):
        if not self.coordinator_url or not self.ngrok_url:
            return False
        async with httpx.AsyncClient(timeout=config.HEALTH_CHECK_TIMEOUT) as client:
            try:
                resp = await client.post(
                    f"{self.coordinator_url}/api/workers/register",
                    json={"name": self.name, "url": self.ngrok_url},
                )
                if resp.status_code == 200:
                    self.registered = True
                    return True
            except Exception:
                pass
        return False

    async def deregister(self):
        if not self.coordinator_url or not self.registered:
            return
        async with httpx.AsyncClient(timeout=config.HEALTH_CHECK_TIMEOUT) as client:
            try:
                await client.delete(
                    f"{self.coordinator_url}/api/workers/{self.name}",
                )
            except Exception:
                pass
        self.registered = False

    async def send_heartbeat(self):
        if not self.coordinator_url or not self.registered:
            return
        async with httpx.AsyncClient(timeout=config.HEALTH_CHECK_TIMEOUT) as client:
            try:
                await client.post(
                    f"{self.coordinator_url}/api/workers/{self.name}/heartbeat",
                    json={"url": self.ngrok_url},
                )
            except Exception:
                pass

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(config.WORKER_HEARTBEAT_INTERVAL)
            await self.send_heartbeat()

    async def start_heartbeat(self):
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        await self.deregister()

    def get_info(self) -> dict:
        return {
            "name": self.name,
            "ngrok_url": self.ngrok_url,
            "coordinator_url": self.coordinator_url,
            "registered": self.registered,
        }
