"""Модуль для определения использования CAT-систем на сайтах компаний."""

import re
from typing import Dict, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from src.utils.helpers import get_random_user_agent, delay


# Ключевые слова, указывающие на использование CAT-систем
CAT_KEYWORDS = [
    # CAT-системы
    'cat-систем', 'cat система', 'cat system',
    'translation memory', 'tm', 'translation memory system',
    'tms', 'translation management system',
    'локализац', 'localization',
    'переводческ', 'translation',
    
    # Конкретные CAT-продукты
    'sdl trados', 'trados',
    'memoq', 'memo q',
    'memsource',
    'smartcat',
    'xtm',
    'phrase',
    'wordfast',
    'deja vu', 'dejavu',
    'omega t',
    'cafe trans',
    'matecat',
    'crowdin',
    'lokalise',
    
    # Функции
    'терминологическ', 'terminology',
    'сегментац', 'segmentation',
    'память перевод', 'translation memory',
    'qa перев', 'lqa',
    'workflow',
    'переводческ платформ',
]


def check_website_for_cat(website: str, timeout: int = 10) -> Tuple[bool, str, Optional[str]]:
    """
    Проверяет, упоминается ли CAT-система на сайте компании.
    
    Парсит HTML страницы и ищет ключевые слова, связанные с CAT-системами.
    
    Возвращает:
        (has_cat, evidence, product_name) - есть ли CAT, доказательство, название продукта
    """
    if not website or not website.startswith(('http://', 'https://')):
        return False, "", None
    
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        delay(1.0)  # Вежливость к серверам
        
        # Выполняем HTTP-запрос к сайту компании
        response = requests.get(website, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # Проверяем тип контента
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type:
            return False, "", None
        
        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Извлекаем текст из основных областей контента
        text_content = ""
        
        # Проверяем основные секции страницы
        for selector in ['main', 'article', '.content', '#content', '.main-content', 'body']:
            elements = soup.select(selector)
            if elements:
                text_content += " " + elements[0].get_text(separator=' ', strip=True)
        
        # Также проверяем навигацию и разделы услуг
        for selector in ['nav', '.services', '.about', '.technologies', '.solutions']:
            elements = soup.select(selector)
            for elem in elements:
                text_content += " " + elem.get_text(separator=' ', strip=True)
        
        # Нормализуем текст (в нижний регистр)
        text_content = text_content.lower()
        
        # Ищем ключевые слова
        found_keywords = []
        found_product = None
        
        for keyword in CAT_KEYWORDS:
            if keyword.lower() in text_content:
                found_keywords.append(keyword)
                
                # Проверяем, является ли это названием продукта
                if keyword.lower() in ['sdl trados', 'trados', 'memoq', 'memsource', 
                                      'smartcat', 'xtm', 'phrase', 'wordfast', 
                                      'deja vu', 'dejavu', 'omega t', 'cafe trans',
                                      'matecat', 'crowdin', 'lokalise']:
                    found_product = keyword.title()
        
        if found_keywords:
            # Формируем доказательство
            evidence_parts = []
            if found_product:
                evidence_parts.append(f"Упоминание продукта {found_product}")
            else:
                evidence_parts.append("Упоминание CAT/TMS/локализации")
            
            # Пытаемся найти контекст упоминания
            for keyword in found_keywords[:3]:  # Первые 3 ключевых слова
                pattern = re.compile(r'.{0,50}' + re.escape(keyword) + r'.{0,50}', re.IGNORECASE)
                matches = pattern.findall(text_content)
                if matches:
                    context = matches[0].strip()
                    if len(context) > 20:
                        evidence_parts.append(f"контекст: {context[:100]}")
                        break
            
            evidence = " | ".join(evidence_parts)
            return True, evidence, found_product
        
        return False, "", None
        
    except requests.exceptions.RequestException as e:
        # Сайт недоступен или ошибка запроса
        return False, f"Ошибка доступа к сайту: {str(e)[:50]}", None
    except Exception as e:
        return False, f"Ошибка парсинга: {str(e)[:50]}", None


def detect_cat_from_description(description: str) -> Tuple[bool, str, Optional[str]]:
    """
    Определяет CAT-систему из текстового описания.
    
    Анализирует текст на наличие ключевых слов, связанных с CAT-системами.
    
    Возвращает:
        (has_cat, evidence, product_name) - есть ли CAT, доказательство, название продукта
    """
    if not description:
        return False, "", None
    
    text_lower = description.lower()
    found_keywords = []
    found_product = None
    
    for keyword in CAT_KEYWORDS:
        if keyword.lower() in text_lower:
            found_keywords.append(keyword)
            
            if keyword.lower() in ['sdl trados', 'trados', 'memoq', 'memsource', 
                                  'smartcat', 'xtm', 'phrase', 'wordfast']:
                found_product = keyword.title()
    
    if found_keywords:
        evidence = f"Упоминание в описании: {', '.join(found_keywords[:3])}"
        return True, evidence, found_product
    
    return False, "", None




