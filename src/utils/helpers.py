"""Вспомогательные функции для работы с данными"""
import re
import time
from typing import Optional
from fake_useragent import UserAgent


ua = UserAgent()


def normalize_revenue(revenue_str: Optional[str]) -> Optional[int]:
    """Нормализует строку выручки в число (рубли)"""
    if not revenue_str:
        return None
    
    # Удаляем все нецифровые символы кроме минуса
    revenue_clean = re.sub(r'[^\d-]', '', str(revenue_str))
    
    if not revenue_clean or revenue_clean == '-':
        return None
    
    try:
        revenue = int(revenue_clean)
        # Если выручка отрицательная, возвращаем None
        if revenue < 0:
            return None
        return revenue
    except ValueError:
        return None


def normalize_inn(inn_str: Optional[str]) -> Optional[str]:
    """Нормализует ИНН (удаляет пробелы, приводит к строке)"""
    if not inn_str:
        return None
    
    inn_clean = re.sub(r'[^\d]', '', str(inn_str))
    if len(inn_clean) in [10, 12]:
        return inn_clean
    return None


def normalize_employees(employees_str: Optional[str]) -> Optional[int]:
    """Нормализует количество сотрудников"""
    if not employees_str:
        return None
    
    # Извлекаем первое число из строки
    match = re.search(r'\d+', str(employees_str))
    if match:
        try:
            return int(match.group())
        except ValueError:
            return None
    return None


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Нормализует URL"""
    if not url:
        return None
    
    url = str(url).strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    return url


def get_headers() -> dict:
    """Возвращает заголовки для HTTP-запросов"""
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }


def sleep_random(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Случайная задержка между запросами"""
    import random
    time.sleep(random.uniform(min_seconds, max_seconds))

