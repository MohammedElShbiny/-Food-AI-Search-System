import json
import os
import uuid
from datetime import datetime
from models import APIKey
import config


class APIKeyManager:
    def __init__(self):
        self.keys_file = config.API_KEYS_FILE
        if not os.path.exists(self.keys_file):
            self._save([])

    def _load(self) -> list[dict]:
        with open(self.keys_file, "r") as f:
            return json.load(f)

    def _save(self, data: list[dict]):
        with open(self.keys_file, "w") as f:
            json.dump(data, f, indent=2)

    def generate_key(self, name: str) -> APIKey:
        key = f"food_ai_{uuid.uuid4().hex}"
        api_key = APIKey(key=key, name=name, created_at=datetime.now().isoformat())
        data = self._load()
        data.append(api_key.model_dump())
        self._save(data)
        return api_key

    def validate_key(self, key: str) -> bool:
        data = self._load()
        for item in data:
            if item["key"] == key and item["is_active"]:
                return True
        return False

    def revoke_key(self, key: str) -> bool:
        data = self._load()
        for item in data:
            if item["key"] == key:
                item["is_active"] = False
                self._save(data)
                return True
        return False

    def list_keys(self) -> list[APIKey]:
        data = self._load()
        return [APIKey(**item) for item in data]
