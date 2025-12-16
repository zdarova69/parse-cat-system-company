"""Поиск конкретных компаний на rusprofile.ru по названиям"""
from typing import List, Dict, Optional
from urllib.parse import quote
from src.collectors.base_collector import BaseCollector
from src.utils.helpers import normalize_revenue, normalize_inn, normalize_employees, normalize_url
import re


class CompanySearcher(BaseCollector):
    """Поиск конкретных компаний по названиям на rusprofile.ru"""
    
    BASE_URL = "https://www.rusprofile.ru"
    
    def search_companies(self, query: str, max_results: int = 50) -> List[Dict]:
        """Реализация абстрактного метода - поиск по названию компании"""
        return [self.search_company_by_name(query)] if self.search_company_by_name(query) else []
    
    def search_company_by_name(self, company_name: str) -> Optional[Dict]:
        """Ищет компанию по названию на rusprofile.ru с использованием регулярных выражений"""
        # Очищаем название от лишних символов
        clean_name = company_name.strip()
        if not clean_name:
            return None
        
        # Пробуем основной вариант поиска
        search_url = f"{self.BASE_URL}/search?query={quote(clean_name)}"
        
        soup = self.fetch_page(search_url)
        if not soup:
            return None
        
        try:
            # Получаем весь HTML как текст для поиска с помощью регулярных выражений
            html_text = str(soup)
            name_lower = clean_name.lower()
            name_words = [w for w in name_lower.split() if len(w) > 2]
            
            # Ищем ИНН в результатах поиска с помощью регулярных выражений
            # Паттерн для поиска ссылок с ИНН: /inn/XXXXXXXXXX или /id/XXXXX
            # Более точный паттерн - ищем ссылки вида href="/inn/XXXXXXXXXX"
            inn_pattern = r'href=["\']?/inn/(\d{10,12})["\']?'
            inn_matches = re.finditer(inn_pattern, html_text, re.IGNORECASE)
            
            found_inns = set()  # Чтобы не проверять один ИНН дважды
            
            for match in inn_matches:
                inn = match.group(1)
                # Проверяем валидность ИНН (10 или 12 цифр)
                if len(inn) not in [10, 12] or inn in found_inns:
                    continue
                
                found_inns.add(inn)
                
                # Ищем контекст вокруг ИНН (название компании должно быть рядом)
                start_pos = max(0, match.start() - 500)
                end_pos = min(len(html_text), match.end() + 500)
                context = html_text[start_pos:end_pos].lower()
                
                # Проверяем, есть ли название компании в контексте
                if (name_lower in context or 
                    (len(name_words) > 0 and sum(1 for w in name_words if w in context) >= len(name_words) * 0.5)):
                    # Пробуем получить данные по ИНН
                    inn_url = f"{self.BASE_URL}/inn/{inn}"
                    company_data = self.get_company_data(inn_url)
                    if company_data:
                        company_name_lower = company_data.get('name', '').lower()
                        if (name_lower in company_name_lower or 
                            len(name_words) > 0 and sum(1 for w in name_words if w in company_name_lower) >= len(name_words) * 0.5):
                            return company_data
            
            # Также пробуем найти через ссылки (старый метод как запасной)
            company_links = soup.find_all('a', href=True)
            for link in company_links[:30]:  # Увеличиваем количество проверок
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if '/id/' in href or '/inn/' in href:
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
            print(f"      Ошибка при поиске компании {clean_name}: {e}")
        
        return None
    
    def get_company_data(self, company_url: str) -> Optional[Dict]:
        """Получение данных о компании с rusprofile.ru с использованием регулярных выражений"""
        soup = self.fetch_page(company_url)
        if not soup:
            return None
        
        try:
            # Получаем HTML как текст для поиска с помощью регулярных выражений
            html_text = str(soup)
            page_text = soup.get_text()
            
            # Извлечение ИНН с помощью регулярных выражений
            inn = None
            # Пробуем найти ИНН в URL
            if '/inn/' in company_url:
                inn_match = re.search(r'/inn/(\d{10,12})', company_url)
                if inn_match:
                    inn = normalize_inn(inn_match.group(1))
            
            # Если ИНН не найден, ищем на странице с помощью регулярных выражений
            if not inn:
                # Паттерны для поиска ИНН
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
            
            # Название компании - ищем в различных местах
            name = None
            # Сначала пробуем через BeautifulSoup
            name_elem = soup.find('h1') or soup.find('title')
            if name_elem:
                name = name_elem.get_text(strip=True)
            
            # Если не нашли, ищем с помощью регулярных выражений
            if not name or len(name) < 3:
                name_patterns = [
                    r'<h1[^>]*>([^<]+)</h1>',
                    r'<title>([^<]+)</title>',
                    r'company-name[^>]*>([^<]+)',
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
                r'выручка[^<]*>(\d+(?:\s*\d+)*)',
                r'<[^>]*>(\d+(?:\s*\d+)*)\s*руб[^<]*выручка',
            ]
            
            for pattern in revenue_patterns:
                match = re.search(pattern, html_text, re.IGNORECASE)
                if match:
                    revenue_str = match.group(1).replace(' ', '').replace('\xa0', '')
                    revenue = normalize_revenue(revenue_str)
                    if revenue:
                        break
            
            # Сайт - ищем с помощью регулярных выражений
            site = None
            # Паттерны для поиска сайта (более точные)
            site_patterns = [
                r'сайт[:\s</>]*https?://([^\s<"\'<>]+)',
                r'сайт[:\s</>]*www\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'href=["\'](https?://(?!baturin|rusprofile|yandex|google|facebook|vk|twitter|linkedin)[^"\']+)["\']',
                r'www\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?!.*rusprofile|.*yandex|.*google)',
            ]
            
            for pattern in site_patterns:
                matches = re.finditer(pattern, html_text, re.IGNORECASE)
                for match in matches:
                    href = match.group(1) if match.lastindex >= 1 else match.group(0)
                    # Исключаем известные домены
                    if any(domain in href.lower() for domain in ['facebook', 'vk.com', 'twitter', 'linkedin', 'rusprofile.ru', 'yandex.ru', 'google.com', 'baturin.ru', 'list-org.com', 'nalog.gov.ru']):
                        continue
                    if not href.startswith('http'):
                        href = 'http://' + href
                    site = normalize_url(href)
                    if site and 'baturin' not in site.lower():
                        break
                if site and 'baturin' not in site.lower():
                    break
            
            # Сотрудники - ищем с помощью регулярных выражений
            employees = None
            employees_patterns = [
                r'(\d+)\s*сотрудник',
                r'сотрудник[:\s</>]*(\d+)',
                r'персонал[:\s</>]*(\d+)',
            ]
            for pattern in employees_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    employees = normalize_employees(match.group(1))
                    if employees:
                        break
            
            # ОКВЭД - ищем с помощью регулярных выражений
            okved = None
            okved_patterns = [
                r'ОКВЭД[:\s</>]*(\d{2}\.\d{2}\.\d{2})',
                r'оквэд[:\s</>]*(\d{2}\.\d{2}\.\d{2})',
                r'(\d{2}\.\d{2}\.\d{2})[^<]*оквэд',
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
                    'source': 'rusprofile'
                }
        except Exception as e:
            print(f"Ошибка при парсинге {company_url}: {e}")
        
        return None
    
    def search_multiple_companies(self, company_names: List[str], 
                                  list_org_collector=None, 
                                  nalog_collector=None) -> List[Dict]:
        """
        Ищет несколько компаний по списку названий с каскадным поиском:
        1. rusprofile.ru
        2. list-org.com
        3. bo.nalog.gov.ru
        4. Если не найдена - добавляет без реквизитов
        """
        companies = []
        for name in company_names:
            print(f"   Поиск: {name}")
            company = None
            source = None
            
            # 1. Пробуем найти на rusprofile.ru
            company = self.search_company_by_name(name)
            if company:
                source = 'rusprofile'
                print(f"      ✓ Найдена на rusprofile.ru: {company.get('name')} (ИНН: {company.get('inn')})")
            else:
                # 2. Пробуем найти на list-org.com
                if list_org_collector:
                    try:
                        company = list_org_collector.search_company_by_name(name)
                        if company:
                            source = 'list-org'
                            print(f"      ✓ Найдена на list-org.com: {company.get('name')} (ИНН: {company.get('inn')})")
                    except Exception as e:
                        print(f"      Ошибка поиска на list-org.com: {e}")
                
                # 3. Пробуем найти на bo.nalog.gov.ru
                if not company and nalog_collector:
                    try:
                        company = nalog_collector.search_company_by_name(name)
                        if company:
                            source = 'nalog.gov.ru'
                            print(f"      ✓ Найдена на nalog.gov.ru: {company.get('name')} (ИНН: {company.get('inn')})")
                    except Exception as e:
                        print(f"      Ошибка поиска на nalog.gov.ru: {e}")
                
                # 4. Если не найдена нигде - добавляем без реквизитов
                if not company:
                    company = {
                        'inn': None,
                        'name': name,
                        'revenue': None,
                        'site': None,
                        'employees': None,
                        'okved_main': None,
                        'source': 'manual'
                    }
                    source = 'manual'
                    print(f"      ⚠ Не найдена, добавлена без реквизитов: {name}")
            
            if company:
                if source:
                    company['source'] = source
                companies.append(company)
        
        return companies

