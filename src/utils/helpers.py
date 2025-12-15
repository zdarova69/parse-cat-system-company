"""Утилиты для обработки данных."""

import re
import time
from typing import Optional
from fake_useragent import UserAgent


def normalize_revenue(revenue_str: str) -> Optional[int]:
    """
    Нормализует строку с выручкой в целое число (в рублях).
    
    Примеры:
        "100 000 000" -> 100000000
        "100.5 млн" -> 100500000
        "1,234,567" -> 1234567
    """
    if not revenue_str or not isinstance(revenue_str, str):
        return None
    
    # Удаляем все пробелы
    revenue_str = revenue_str.replace(' ', '').replace('\xa0', '')
    
    # Обработка миллионов
    if 'млн' in revenue_str.lower() or 'million' in revenue_str.lower():
        # Извлекаем число
        numbers = re.findall(r'[\d,\.]+', revenue_str)
        if numbers:
            num_str = numbers[0].replace(',', '.').replace(' ', '')
            try:
                num = float(num_str)
                return int(num * 1_000_000)
            except ValueError:
                return None
    
    # Обработка миллиардов
    if 'млрд' in revenue_str.lower() or 'billion' in revenue_str.lower():
        numbers = re.findall(r'[\d,\.]+', revenue_str)
        if numbers:
            num_str = numbers[0].replace(',', '.').replace(' ', '')
            try:
                num = float(num_str)
                return int(num * 1_000_000_000)
            except ValueError:
                return None
    
    # Извлекаем все цифры
    digits = re.sub(r'[^\d]', '', revenue_str)
    if digits:
        try:
            return int(digits)
        except ValueError:
            return None
    
    return None


def normalize_inn(inn_str: str) -> Optional[str]:
    """Нормализует ИНН до строки из 10 или 12 цифр."""
    if not inn_str:
        return None
    
    # Извлекаем только цифры
    digits = re.sub(r'[^\d]', '', str(inn_str))
    
    # ИНН должен быть 10 или 12 цифр
    if len(digits) in [10, 12]:
        return digits
    
    return None


def normalize_name(name: str) -> str:
    """Нормализует название компании - удаляет лишние пробелы, обрезает."""
    if not name:
        return ""
    
    # Удаляем лишние пробелы
    name = re.sub(r'\s+', ' ', str(name))
    return name.strip()


def get_random_user_agent() -> str:
    """Получает случайный User-Agent для запросов."""
    try:
        ua = UserAgent()
        return ua.random
    except:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def delay(seconds: float = 1.0):
    """Добавляет задержку между запросами."""
    time.sleep(seconds)



