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
        """Ищет компанию по названию на rusprofile.ru"""
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
            # Ищем ссылки на компании в результатах поиска
            company_links = soup.find_all('a', href=True)
            name_lower = clean_name.lower()
            
            for link in company_links[:20]:  # Ограничиваем количество проверок
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Проверяем, что это ссылка на компанию
                if '/id/' in href or '/inn/' in href:
                    text_lower = text.lower()
                    
                    # Проверяем совпадение названия (более гибкая проверка)
                    name_words = [w for w in name_lower.split() if len(w) > 2]
                    if (name_lower in text_lower or 
                        len(name_words) > 0 and sum(1 for w in name_words if w in text_lower) >= len(name_words) * 0.5):
                        company_url = href if href.startswith('http') else self.BASE_URL + href
                        company_data = self.get_company_data(company_url)
                        if company_data:
                            # Проверяем, что название действительно похоже
                            company_name_lower = company_data.get('name', '').lower()
                            if (name_lower in company_name_lower or 
                                len(name_words) > 0 and sum(1 for w in name_words if w in company_name_lower) >= len(name_words) * 0.5):
                                return company_data
        
        except Exception as e:
            print(f"      Ошибка при поиске компании {clean_name}: {e}")
        
        return None
    
    def get_company_data(self, company_url: str) -> Optional[Dict]:
        """Получение данных о компании с rusprofile.ru"""
        soup = self.fetch_page(company_url)
        if not soup:
            return None
        
        try:
            # Извлечение ИНН
            inn = None
            # Пробуем найти ИНН в URL
            if '/inn/' in company_url:
                inn_match = company_url.split('/inn/')[-1].split('/')[0]
                inn = normalize_inn(inn_match)
            
            # Если ИНН не найден, ищем на странице
            if not inn:
                inn_elem = soup.find(string=lambda x: x and 'ИНН' in str(x))
                if inn_elem:
                    inn_text = inn_elem.find_next('span') or inn_elem.find_next('div')
                    if inn_text:
                        inn = normalize_inn(inn_text.get_text())
            
            # Название компании
            name_elem = soup.find('h1') or soup.find('div', class_=lambda x: x and 'company-name' in str(x).lower() if x else False)
            name = name_elem.get_text(strip=True) if name_elem else None
            
            # Выручка - ищем в различных форматах
            revenue = None
            revenue_patterns = [
                r'выручка[:\s]*(\d+(?:\s*\d+)*)',
                r'доход[:\s]*(\d+(?:\s*\d+)*)',
                r'(\d+(?:\s*\d+)*)\s*руб[.\s]*выручка',
            ]
            
            page_text = soup.get_text()
            for pattern in revenue_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    revenue_str = match.group(1).replace(' ', '')
                    revenue = normalize_revenue(revenue_str)
                    if revenue:  # Сохраняем любую выручку, фильтрация будет позже
                        break
            
            # Сайт
            site = None
            site_links = soup.find_all('a', href=lambda x: x and ('http://' in str(x) or 'https://' in str(x)))
            for link in site_links:
                href = link.get('href', '')
                # Исключаем ссылки на социальные сети и внутренние ссылки
                if not any(domain in href.lower() for domain in ['facebook', 'vk.com', 'twitter', 'linkedin', 'rusprofile.ru']):
                    site = normalize_url(href)
                    break
            
            # Сотрудники
            employees = None
            employees_match = re.search(r'(\d+)\s*сотрудник', page_text, re.IGNORECASE)
            if employees_match:
                employees = normalize_employees(employees_match.group(1))
            
            # ОКВЭД
            okved = None
            okved_match = re.search(r'ОКВЭД[:\s]*(\d{2}\.\d{2}\.\d{2})', page_text, re.IGNORECASE)
            if okved_match:
                okved = okved_match.group(1)
            
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

