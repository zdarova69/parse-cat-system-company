"""Коллектор данных с bo.nalog.gov.ru (официальный сайт ФНС)"""
import re
from typing import List, Dict, Optional
from urllib.parse import quote
from src.collectors.base_collector import BaseCollector
from src.utils.helpers import normalize_revenue, normalize_inn, normalize_employees, normalize_url


class NalogCollector(BaseCollector):
    """Коллектор для bo.nalog.gov.ru"""
    
    BASE_URL = "https://bo.nalog.gov.ru"
    
    def search_companies(self, query: str, max_results: int = 50) -> List[Dict]:
        """Поиск компаний на bo.nalog.gov.ru"""
        companies = []
        search_url = f"{self.BASE_URL}/search?query={quote(query)}"
        
        soup = self.fetch_page(search_url)
        if not soup:
            return companies
        
        # Ищем ссылки на компании
        company_links = soup.find_all('a', href=True)
        for link in company_links[:max_results]:
            href = link.get('href', '')
            if '/company/' in href or '/inn/' in href:
                company_url = href if href.startswith('http') else self.BASE_URL + href
                company_data = self.get_company_data(company_url)
                if company_data:
                    companies.append(company_data)
                    if len(companies) >= max_results:
                        break
        
        return companies
    
    def search_company_by_name(self, company_name: str) -> Optional[Dict]:
        """Ищет компанию по названию на bo.nalog.gov.ru"""
        search_url = f"{self.BASE_URL}/search?query={quote(company_name)}"
        
        soup = self.fetch_page(search_url)
        if not soup:
            return None
        
        try:
            # Ищем ссылки на компании в результатах поиска
            company_links = soup.find_all('a', href=True)
            name_lower = company_name.lower()
            
            for link in company_links[:20]:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if '/company/' in href or '/inn/' in href:
                    text_lower = text.lower()
                    name_words = [w for w in name_lower.split() if len(w) > 2]
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
            print(f"      Ошибка при поиске на nalog.gov.ru: {e}")
        
        return None
    
    def get_company_data(self, company_url: str) -> Optional[Dict]:
        """Получение данных о компании с bo.nalog.gov.ru"""
        soup = self.fetch_page(company_url)
        if not soup:
            return None
        
        try:
            # ИНН
            inn = None
            if '/inn/' in company_url:
                inn_match = company_url.split('/inn/')[-1].split('/')[0]
                inn = normalize_inn(inn_match)
            
            if not inn:
                inn_elem = soup.find(string=lambda x: x and 'ИНН' in str(x))
                if inn_elem:
                    parent = inn_elem.find_parent()
                    if parent:
                        inn_text = parent.get_text()
                        inn = normalize_inn(inn_text)
            
            # Название
            name_elem = soup.find('h1') or soup.find('title')
            name = name_elem.get_text(strip=True) if name_elem else None
            
            # Выручка (на nalog.gov.ru может быть не указана)
            revenue = None
            revenue_elem = soup.find(string=lambda x: x and ('выручка' in str(x).lower() or 'доход' in str(x).lower()))
            if revenue_elem:
                parent = revenue_elem.find_parent()
                if parent:
                    revenue_text = parent.get_text()
                    revenue = normalize_revenue(revenue_text)
            
            # Сайт
            site = None
            site_elem = soup.find('a', href=lambda x: x and ('http://' in str(x) or 'https://' in str(x)))
            if site_elem:
                site = normalize_url(site_elem.get('href'))
            
            # Сотрудники
            employees = None
            employees_elem = soup.find(string=lambda x: x and 'сотрудник' in str(x).lower())
            if employees_elem:
                parent = employees_elem.find_parent()
                if parent:
                    employees_text = parent.get_text()
                    employees = normalize_employees(employees_text)
            
            # ОКВЭД
            okved = None
            okved_elem = soup.find(string=lambda x: x and 'оквэд' in str(x).lower())
            if okved_elem:
                parent = okved_elem.find_parent()
                if parent:
                    okved_text = parent.get_text()
                    okved_match = re.search(r'\d{2}\.\d{2}\.\d{2}', okved_text)
                    if okved_match:
                        okved = okved_match.group()
            
            if inn and name:
                return {
                    'inn': inn,
                    'name': name.strip(),
                    'revenue': revenue,
                    'site': site,
                    'employees': employees,
                    'okved_main': okved,
                    'source': 'nalog.gov.ru'
                }
        except Exception as e:
            print(f"Ошибка при парсинге {company_url}: {e}")
        
        return None

