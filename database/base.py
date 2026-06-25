from abc import ABC, abstractmethod
from models import Food


class DatabaseInterface(ABC):

    @abstractmethod
    def search(self, query: str) -> list[Food]:
        pass

    @abstractmethod
    def get_all(self) -> list[Food]:
        pass

    @abstractmethod
    def add_food(self, food: Food) -> bool:
        pass

    @abstractmethod
    def delete_food(self, food_id: str) -> bool:
        pass

    @abstractmethod
    def food_exists(self, food_id: str) -> bool:
        pass

    @abstractmethod
    def get_table_info(self) -> list[dict]:
        pass

    @abstractmethod
    def get_table_data(self, table_name: str, page: int = 1, per_page: int = 50) -> dict:
        pass

    @abstractmethod
    def get_db_stats(self) -> dict:
        pass

    @abstractmethod
    def execute_readonly_query(self, sql: str) -> dict:
        pass
