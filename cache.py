import hashlib
import json
import time
import sqlite3
from collections import OrderedDict
import config


class SearchCache:
    def __init__(self):
        self._memory: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._max_items = config.CACHE_MAX_MEMORY
        self._ttl = config.CACHE_TTL
        self._total_queries = 0
        self._cache_hits = 0
        self._initialized = False

    def _ensure_table(self):
        if self._initialized:
            return
        conn = sqlite3.connect(config.SQLITE_PATH)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    lang TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 1
                )
            """)
            conn.commit()
        finally:
            conn.close()
        self._initialized = True

    def _hash(self, query: str, lang: str) -> str:
        raw = f"{query.lower().strip()}:{lang}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    async def get(self, query: str, lang: str) -> dict | None:
        self._ensure_table()
        self._total_queries += 1
        key = self._hash(query, lang)

        if key in self._memory:
            data_json, ts = self._memory[key]
            if time.time() - ts < self._ttl:
                self._cache_hits += 1
                self._memory.move_to_end(key)
                return json.loads(data_json)
            else:
                del self._memory[key]

        conn = sqlite3.connect(config.SQLITE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response_json, created_at FROM search_cache WHERE query_hash = ?",
                (key,),
            )
            row = cursor.fetchone()
            if row:
                created = row[1]
                try:
                    ts = time.mktime(time.strptime(created, "%Y-%m-%d %H:%M:%S"))
                except ValueError:
                    ts = 0
                if time.time() - ts < self._ttl:
                    self._cache_hits += 1
                    self._memory[key] = (row[0], time.time())
                    if len(self._memory) > self._max_items:
                        self._memory.popitem(last=False)
                    return json.loads(row[0])
                else:
                    cursor.execute("DELETE FROM search_cache WHERE query_hash = ?", (key,))
                    conn.commit()
        finally:
            conn.close()

        return None

    async def set(self, query: str, lang: str, response: dict):
        self._ensure_table()
        key = self._hash(query, lang)
        data_json = json.dumps(response, ensure_ascii=False)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        self._memory[key] = (data_json, time.time())
        if len(self._memory) > self._max_items:
            self._memory.popitem(last=False)

        conn = sqlite3.connect(config.SQLITE_PATH)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO search_cache (query_hash, query, lang, response_json, created_at, hit_count) "
                "VALUES (?, ?, ?, ?, ?, COALESCE((SELECT hit_count FROM search_cache WHERE query_hash = ?) + 1, 1))",
                (key, query, lang, data_json, now, key),
            )
            conn.commit()
        finally:
            conn.close()

    async def invalidate(self, query: str = None):
        self._ensure_table()
        if query:
            key = self._hash(query, "en")
            key_ar = self._hash(query, "ar")
            self._memory.pop(key, None)
            self._memory.pop(key_ar, None)
            conn = sqlite3.connect(config.SQLITE_PATH)
            try:
                conn.execute("DELETE FROM search_cache WHERE query_hash IN (?, ?)", (key, key_ar))
                conn.commit()
            finally:
                conn.close()
        else:
            self._memory.clear()
            conn = sqlite3.connect(config.SQLITE_PATH)
            try:
                conn.execute("DELETE FROM search_cache")
                conn.commit()
            finally:
                conn.close()

    async def stats(self) -> dict:
        self._ensure_table()
        conn = sqlite3.connect(config.SQLITE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM search_cache")
            db_count = cursor.fetchone()[0]
        finally:
            conn.close()

        hit_rate = (self._cache_hits / self._total_queries * 100) if self._total_queries > 0 else 0
        return {
            "memory_entries": len(self._memory),
            "db_entries": db_count,
            "total_queries": self._total_queries,
            "cache_hits": self._cache_hits,
            "hit_rate": round(hit_rate, 2),
        }


cache = SearchCache()
