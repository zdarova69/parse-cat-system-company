"""Базовый класс для коллекторов данных"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup
from src.utils.helpers import get_headers, sleep_random


class BaseCollector(ABC):
    """Базовый класс для всех коллекторов"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(get_headers())
    
    def fetch_page(self, url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
        """Получает HTML страницу и парсит её"""
        try:
            sleep_random(1.0, 2.5)
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            # Не выводим ошибку для 404, просто возвращаем None
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except HTTPError as e:
            if hasattr(e, 'response') and e.response.status_code == 404:
                return None
            # Для других ошибок не выводим сообщение
            return None
        except Exception:
            # Молча игнорируем другие ошибки
            return None
    
    @abstractmethod
    def search_companies(self, query: str, max_results: int = 50) -> List[Dict]:
        """Поиск компаний по запросу"""
        pass
    
    @abstractmethod
    def get_company_data(self, company_url: str) -> Optional[Dict]:
        """Получение данных о компании по URL"""
        pass

