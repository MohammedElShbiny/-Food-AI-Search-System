import sqlite3
import re
from database.base import DatabaseInterface
from models import Food
import config


def is_arabic(query: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', query))


class SQLiteDatabase(DatabaseInterface):
    def __init__(self):
        self.db_path = config.SQLITE_PATH

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _detect_lang(self, query: str) -> str:
        return 'ar' if is_arabic(query) else 'en'

    def search(self, query: str) -> list[Food]:
        lang = self._detect_lang(query)
        return self._search_by_lang(query, lang)

    def _search_by_lang(self, query: str, lang: str) -> list[Food]:
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
                FROM aliases a
                JOIN foods f ON a.food_id = f.food_id
                WHERE a.normalized LIKE ? AND a.lang = ?
            """, (f"%{query.lower()}%", lang))
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
                "INSERT INTO foods (food_id, name_en, name_ar, category_en, category_ar, serving_description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (food.food_id, food.name_en, food.name_ar,
                 food.category_en, food.category_ar, food.serving_description),
            )
            cursor.execute(
                "INSERT INTO nutrient_records (food_id, source_id, field, value, per_serving) "
                "VALUES (?, 'curated_v1', 'carbs', ?, 1)",
                (food.food_id, food.carbs),
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
