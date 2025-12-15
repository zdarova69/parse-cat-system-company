"""Базовый класс для сборщиков данных."""

from abc import ABC, abstractmethod
from typing import List, Dict
from src.utils.helpers import delay, get_random_user_agent
import requests


class BaseCollector(ABC):
    """Базовый класс для всех сборщиков данных."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        })
    
    @abstractmethod
    def collect(self, query: str = None, limit: int = 100) -> List[Dict]:
        """
        Собирает данные о компаниях.
        
        Возвращает список словарей с полями:
        - inn, name, revenue, site, cat_evidence, source
        - Опционально: cat_product, employees, okved_main
        """
        pass
    
    def make_request(self, url: str, **kwargs) -> requests.Response:
        """Выполняет HTTP-запрос с обработкой ошибок."""
        delay(1.5)  # Вежливость к серверам
        
        try:
            response = self.session.get(url, timeout=10, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса для {url}: {e}")
            raise



