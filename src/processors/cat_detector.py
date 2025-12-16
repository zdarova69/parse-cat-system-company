"""Детектор CAT-систем на сайтах компаний"""
import re
from typing import Optional, Dict, Tuple
import requests
from bs4 import BeautifulSoup
from src.utils.helpers import normalize_url, get_headers, sleep_random


class CATDetector:
    """Класс для определения наличия CAT-систем на сайте компании"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(get_headers())
    
    def fetch_page(self, url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
        """Получает HTML страницу и парсит её"""
        try:
            sleep_random(1.0, 2.5)
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            print(f"Ошибка при загрузке {url}: {e}")
            return None
    
    # Ключевые слова для поиска CAT-систем
    CAT_KEYWORDS = [
        'cat-систем', 'cat систем', 'cat система',
        'translation memory', 'tm', 'tms', 'translation management',
        'локализационн', 'локализац', 'localization',
        'переводческ', 'переводн', 'translation',
        'memsource', 'smartcat', 'sdl trados', 'trados',
        'memoq', 'phrase', 'xtm', 'crowdin', 'lokalise',
        'wordfast', 'omegat', 'deja vu',
        'терминологическ', 'терминолог',
        'память перевод', 'memory перевод',
        'workflow перевод', 'процесс перевод',
        'qa перевод', 'lqa', 'quality assurance',
        'сегментац', 'сегмент',
    ]
    
    # Названия конкретных продуктов
    CAT_PRODUCTS = {
        'sdl trados': 'SDL Trados',
        'trados': 'SDL Trados',
        'memoq': 'MemoQ',
        'memsource': 'Memsource',
        'smartcat': 'Smartcat',
        'xtm': 'XTM',
        'phrase': 'Phrase',
        'crowdin': 'Crowdin',
        'lokalise': 'Lokalise',
        'wordfast': 'Wordfast',
        'omegat': 'OmegaT',
        'deja vu': 'Déjà Vu',
    }
    
    def detect_cat(self, site_url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Определяет наличие CAT-системы на сайте компании
        
        Returns:
            (has_cat, evidence, product_name)
        """
        if not site_url:
            return False, None, None
        
        site_url = normalize_url(site_url)
        if not site_url:
            return False, None, None
        
        try:
            soup = self.fetch_page(site_url, timeout=8)
            if not soup:
                return False, None, None
            
            # Получаем весь текст страницы
            page_text = soup.get_text().lower()
            
            # Ищем упоминания CAT-систем
            found_keywords = []
            found_product = None
            
            for keyword in self.CAT_KEYWORDS:
                if keyword.lower() in page_text:
                    found_keywords.append(keyword)
            
            # Ищем конкретные продукты
            for product_key, product_name in self.CAT_PRODUCTS.items():
                if product_key.lower() in page_text:
                    found_product = product_name
                    break
            
            if found_keywords or found_product:
                # Формируем доказательство
                evidence_parts = []
                
                # Проверяем разделы сайта
                sections = []
                for section in ['технологи', 'услуг', 'о нас', 'about', 'services', 'technology']:
                    if section in page_text:
                        sections.append(section)
                
                if sections:
                    evidence_parts.append(f"Упоминание в разделе '{sections[0]}'")
                
                if found_product:
                    evidence_parts.append(f"Использование продукта {found_product}")
                elif found_keywords:
                    evidence_parts.append(f"Упоминание: {found_keywords[0]}")
                
                evidence = " | ".join(evidence_parts) if evidence_parts else "Упоминание CAT/TMS/локализации"
                
                return True, evidence, found_product
            
            return False, None, None
            
        except Exception as e:
            print(f"Ошибка при проверке сайта {site_url}: {e}")
            return False, None, None

