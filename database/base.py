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
