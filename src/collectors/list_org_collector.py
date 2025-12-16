"""Коллектор данных с list-org.com"""
import re
from typing import List, Dict, Optional
from urllib.parse import quote
from src.collectors.base_collector import BaseCollector
from src.utils.helpers import normalize_revenue, normalize_inn, normalize_employees, normalize_url


class ListOrgCollector(BaseCollector):
    """Коллектор для list-org.com"""
    
    BASE_URL = "https://www.list-org.com"
    
    def search_companies(self, query: str, max_results: int = 50) -> List[Dict]:
        """Поиск компаний на list-org.com"""
        companies = []
        search_url = f"{self.BASE_URL}/search?query={quote(query)}"
        
        soup = self.fetch_page(search_url)
        if not soup:
            return companies
        
        # Ищем ссылки на компании
        company_links = soup.find_all('a', href=True)
        for link in company_links[:max_results]:
            href = link.get('href', '')
            if '/company/' in href or '/org/' in href:
                company_url = href if href.startswith('http') else self.BASE_URL + href
                company_data = self.get_company_data(company_url)
                if company_data:
                    companies.append(company_data)
                    if len(companies) >= max_results:
                        break
        
        return companies
    
    def search_company_by_name(self, company_name: str) -> Optional[Dict]:
        """Ищет компанию по названию на list-org.com с использованием регулярных выражений"""
        search_url = f"{self.BASE_URL}/search?query={quote(company_name)}"
        
        soup = self.fetch_page(search_url)
        if not soup:
            return None
        
        try:
            # Получаем HTML как текст для поиска с помощью регулярных выражений
            html_text = str(soup)
            name_lower = company_name.lower()
            name_words = [w for w in name_lower.split() if len(w) > 2]
            
            # Ищем ИНН в результатах поиска с помощью регулярных выражений
            inn_pattern = r'(?:/company/|/org/)(\d+)'
            inn_matches = re.finditer(inn_pattern, html_text)
            
            for match in inn_matches:
                company_id = match.group(1)
                # Ищем контекст вокруг ID
                start_pos = max(0, match.start() - 500)
                end_pos = min(len(html_text), match.end() + 500)
                context = html_text[start_pos:end_pos].lower()
                
                if (name_lower in context or 
                    (len(name_words) > 0 and sum(1 for w in name_words if w in context) >= len(name_words) * 0.5)):
                    company_url = f"{self.BASE_URL}/company/{company_id}"
                    company_data = self.get_company_data(company_url)
                    if company_data:
                        company_name_lower = company_data.get('name', '').lower()
                        if (name_lower in company_name_lower or 
                            len(name_words) > 0 and sum(1 for w in name_words if w in company_name_lower) >= len(name_words) * 0.5):
                            return company_data
            
            # Также пробуем через ссылки
            company_links = soup.find_all('a', href=True)
            for link in company_links[:30]:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if '/company/' in href or '/org/' in href:
                    text_lower = text.lower()
                    if (name_lower in text_lower or 
                        len(name_words) > 0 and sum(1 for w in name_words if w in text_lower) >= len(name_words) * 0.5):
                        company_url = href if href.startswith('http') else self.BASE_URL + href
                        company_data = self.get_company_data(company_url)
                        if company_data:
                            company_name_lower = company_data.get('name', '').lower()
                            if (name_lower in company_name_lower or 
                                len(name_words) > 0 and sum(1 for w in name_words if w in company_name_lower) >= len(name_words) * 0.5):
                                return company_data
        except Exception as e:
            print(f"      Ошибка при поиске на list-org.com: {e}")
        
        return None
    
    def get_company_data(self, company_url: str) -> Optional[Dict]:
        """Получение данных о компании с list-org.com с использованием регулярных выражений"""
        soup = self.fetch_page(company_url)
        if not soup:
            return None
        
        try:
            html_text = str(soup)
            page_text = soup.get_text()
            
            # ИНН - ищем с помощью регулярных выражений
            inn = None
            inn_patterns = [
                r'ИНН[:\s</>]*(\d{10,12})',
                r'ИНН\s*[:\s</>]*(\d{10,12})',
                r'inn[:\s</>]*(\d{10,12})',
                r'<[^>]*>ИНН[:\s]*</[^>]*>[\s<]*(\d{10,12})',
            ]
            for pattern in inn_patterns:
                match = re.search(pattern, html_text, re.IGNORECASE)
                if match:
                    inn = normalize_inn(match.group(1))
                    if inn:
                        break
            
            # Название
            name = None
            name_elem = soup.find('h1') or soup.find('title')
            if name_elem:
                name = name_elem.get_text(strip=True)
            
            if not name or len(name) < 3:
                name_patterns = [
                    r'<h1[^>]*>([^<]+)</h1>',
                    r'<title>([^<]+)</title>',
                    r'название[:\s</>]*([А-Яа-яЁё\s"«»]+)',
                ]
                for pattern in name_patterns:
                    match = re.search(pattern, html_text, re.IGNORECASE)
                    if match:
                        name = match.group(1).strip()
                        if name and len(name) > 3:
                            break
            
            # Выручка - ищем с помощью регулярных выражений
            revenue = None
            revenue_patterns = [
                r'выручка[:\s</>]*(\d+(?:\s*\d+)*)\s*руб',
                r'выручка[:\s</>]*(\d+(?:\s*\d+)*)',
                r'доход[:\s</>]*(\d+(?:\s*\d+)*)\s*руб',
                r'(\d+(?:\s*\d+)*)\s*руб[.\s]*выручка',
            ]
            for pattern in revenue_patterns:
                match = re.search(pattern, html_text, re.IGNORECASE)
                if match:
                    revenue_str = match.group(1).replace(' ', '').replace('\xa0', '')
                    revenue = normalize_revenue(revenue_str)
                    if revenue:
                        break
            
            # Сайт
            site = None
            site_patterns = [
                r'href=["\'](https?://[^"\']+)["\']',
                r'сайт[:\s</>]*https?://([^\s<]+)',
                r'www\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            ]
            for pattern in site_patterns:
                matches = re.finditer(pattern, html_text, re.IGNORECASE)
                for match in matches:
                    href = match.group(1) if match.lastindex >= 1 else match.group(0)
                    if not any(domain in href.lower() for domain in ['facebook', 'vk.com', 'twitter', 'linkedin', 'list-org.com', 'yandex.ru', 'google.com']):
                        if not href.startswith('http'):
                            href = 'http://' + href
                        site = normalize_url(href)
                        if site:
                            break
                if site:
                    break
            
            # Сотрудники
            employees = None
            employees_patterns = [
                r'(\d+)\s*сотрудник',
                r'сотрудник[:\s</>]*(\d+)',
            ]
            for pattern in employees_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    employees = normalize_employees(match.group(1))
                    if employees:
                        break
            
            # ОКВЭД
            okved = None
            okved_patterns = [
                r'ОКВЭД[:\s</>]*(\d{2}\.\d{2}\.\d{2})',
                r'оквэд[:\s</>]*(\d{2}\.\d{2}\.\d{2})',
            ]
            for pattern in okved_patterns:
                match = re.search(pattern, html_text, re.IGNORECASE)
                if match:
                    okved = match.group(1)
                    if okved:
                        break
            
            if inn and name:
                return {
                    'inn': inn,
                    'name': name.strip(),
                    'revenue': revenue,
                    'site': site,
                    'employees': employees,
                    'okved_main': okved,
                    'source': 'list-org'
                }
        except Exception as e:
            print(f"Ошибка при парсинге {company_url}: {e}")
        
        return None

