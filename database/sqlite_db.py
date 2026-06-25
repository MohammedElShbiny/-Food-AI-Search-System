import sqlite3
import os
import re
from database.base import DatabaseInterface
from models import Food
import config


def is_arabic(query: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', query))


class SQLiteDatabase(DatabaseInterface):
    def __init__(self):
        self.db_path = config.SQLITE_PATH
        self._ensure_indexes()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_indexes(self):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliases_normalized ON aliases(normalized)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliases_lang ON aliases(lang)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliases_food_id ON aliases(food_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nutrients_food_field ON nutrient_records(food_id, field)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_foods_food_id ON foods(food_id)")
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def _detect_lang(self, query: str) -> str:
        return 'ar' if is_arabic(query) else 'en'

    def search(self, query: str) -> list[Food]:
        lang = self._detect_lang(query)
        return self._search_by_lang(query, lang)

    def _search_by_lang(self, query: str, lang: str) -> list[Food]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            q = f"%{query.lower()}%"
            cursor.execute("""
                SELECT DISTINCT
                    f.food_id,
                    f.name_en,
                    f.name_ar,
                    COALESCE(
                        (SELECT nr.value FROM nutrient_records nr
                         WHERE nr.food_id = f.food_id AND nr.field = 'carbs'
                         ORDER BY CASE nr.source_id WHEN 'curated_v1' THEN 0 ELSE 1 END
                         LIMIT 1),
                        0
                    ) as carbs,
                    f.category_en,
                    f.category_ar,
                    f.serving_description
                FROM aliases a
                JOIN foods f ON a.food_id = f.food_id
                WHERE (
                    a.normalized LIKE ?
                    OR ? LIKE '%' || a.normalized || '%'
                    OR f.name_en LIKE ?
                    OR f.name_ar LIKE ?
                    OR f.food_id LIKE ?
                )
                AND a.lang = ?
            """, (q, query.lower(), q, q, q, lang))
            rows = cursor.fetchall()
            return [
                Food(
                    food_id=r["food_id"],
                    name_en=r["name_en"],
                    name_ar=r["name_ar"],
                    carbs=r["carbs"],
                    category_en=r["category_en"],
                    category_ar=r["category_ar"],
                    serving_description=r["serving_description"] or "",
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_all(self) -> list[Food]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT
                    f.food_id,
                    f.name_en,
                    f.name_ar,
                    COALESCE(
                        (SELECT nr.value FROM nutrient_records nr
                         WHERE nr.food_id = f.food_id AND nr.field = 'carbs'
                         ORDER BY CASE nr.source_id WHEN 'curated_v1' THEN 0 ELSE 1 END
                         LIMIT 1),
                        0
                    ) as carbs,
                    f.category_en,
                    f.category_ar,
                    f.serving_description
                FROM foods f
            """)
            rows = cursor.fetchall()
            return [
                Food(
                    food_id=r["food_id"],
                    name_en=r["name_en"],
                    name_ar=r["name_ar"],
                    carbs=r["carbs"],
                    category_en=r["category_en"],
                    category_ar=r["category_ar"],
                    serving_description=r["serving_description"] or "",
                )
                for r in rows
            ]
        finally:
            conn.close()

    def add_food(self, food: Food) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO foods (food_id, name_en, name_ar, category_en, category_ar, serving_description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (food.food_id, food.name_en, food.name_ar,
                 food.category_en, food.category_ar, food.serving_description),
            )
            source_id = f"fallback_{food.source}" if food.source != "database" else "curated_v1"
            cursor.execute(
                "SELECT 1 FROM nutrient_records WHERE food_id = ? AND field = 'carbs'",
                (food.food_id,),
            )
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE nutrient_records SET value = ?, source_id = ? "
                    "WHERE food_id = ? AND field = 'carbs'",
                    (food.carbs, source_id, food.food_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO nutrient_records (food_id, source_id, field, value, per_serving) "
                    "VALUES (?, ?, 'carbs', ?, 1)",
                    (food.food_id, source_id, food.carbs),
                )
            for lang, name in [("en", food.name_en), ("ar", food.name_ar)]:
                if name:
                    normalized = name.lower().strip()
                    cursor.execute(
                        "INSERT OR IGNORE INTO aliases (alias_text, lang, food_id, normalized) VALUES (?, ?, ?, ?)",
                        (name, lang, food.food_id, normalized),
                    )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_food(self, food_id: str) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM nutrient_records WHERE food_id = ?", (food_id,))
            cursor.execute("DELETE FROM aliases WHERE food_id = ?", (food_id,))
            cursor.execute("DELETE FROM gi_records WHERE food_id = ?", (food_id,))
            cursor.execute("DELETE FROM foods WHERE food_id = ?", (food_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def food_exists(self, food_id: str) -> bool:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM foods WHERE food_id = ?", (food_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def get_table_info(self) -> list[dict]:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = []
            for row in cursor.fetchall():
                name = row["name"]
                cursor.execute(f"SELECT COUNT(*) as cnt FROM [{name}]")
                count = cursor.fetchone()["cnt"]
                tables.append({"name": name, "row_count": count})
            return tables
        finally:
            conn.close()

    def get_table_data(self, table_name: str, page: int = 1, per_page: int = 50) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = [{"name": r["name"], "type": r["type"]} for r in cursor.fetchall()]

            offset = (page - 1) * per_page
            cursor.execute(f"SELECT * FROM [{table_name}] LIMIT ? OFFSET ?", (per_page, offset))
            rows = [list(r) for r in cursor.fetchall()]

            cursor.execute(f"SELECT COUNT(*) as cnt FROM [{table_name}]")
            total = cursor.fetchone()["cnt"]

            return {
                "columns": [c["name"] for c in columns],
                "rows": rows,
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        finally:
            conn.close()

    def get_db_stats(self) -> dict:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            stats = {"tables": {}, "db_size_bytes": 0}

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            for t in tables:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM [{t}]")
                stats["tables"][t] = cursor.fetchone()["cnt"]

            try:
                stats["db_size_bytes"] = os.path.getsize(self.db_path)
            except OSError:
                pass

            return stats
        finally:
            conn.close()

    def execute_readonly_query(self, sql: str) -> dict:
        sql_upper = sql.strip().upper()
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE"]
        for word in forbidden:
            if sql_upper.startswith(word) or f" {word} " in sql_upper:
                return {"error": f"Read-only mode: {word} statements are not allowed"}

        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [list(r) for r in cursor.fetchall()]
            return {"columns": columns, "rows": rows, "row_count": len(rows)}
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()
