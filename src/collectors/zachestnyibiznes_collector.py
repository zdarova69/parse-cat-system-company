"""Сборщик данных с zachestnyibiznes.ru."""

import re
from typing import List, Dict
from bs4 import BeautifulSoup
from src.collectors.base_collector import BaseCollector
from src.processors.cat_detector import check_website_for_cat
from src.utils.helpers import normalize_revenue, normalize_inn


class ZachestnyibiznesCollector(BaseCollector):
    """Сборщик данных с zachestnyibiznes.ru."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://zachestnyibiznes.ru"
    
    def collect(self, query: str = None, limit: int = 100) -> List[Dict]:
        """
        Собирает компании с zachestnyibiznes.ru.
        
        Парсит результаты поиска по ключевым словам, связанным с переводами и локализацией.
        """
        companies = []
        
        # Поисковые запросы, связанные с переводами и локализацией
        search_queries = [
            "перевод",
            "локализация",
            "translation",
            "localization",
            "лингвистическ",
            "переводческ",
        ]
        
        if query:
            search_queries = [query]
        
        # Парсим результаты поиска для каждого запроса
        for search_query in search_queries:
            if len(companies) >= limit:
                break
            
            try:
                # Формируем URL для поиска
                search_url = f"{self.base_url}/search?query={search_query}"
                print(f"   Парсинг поиска: {search_query}")
                
                # Выполняем запрос
                response = self.make_request(search_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем ссылки на компании в результатах поиска
                company_links = soup.find_all('a', href=re.compile(r'/company/\d+'))
                
                # Если не нашли, пробуем другой селектор
                if not company_links:
                    company_links = soup.find_all('a', href=re.compile(r'/org/\d+'))
                
                for link in company_links[:20]:  # Ограничиваем количество на странице
                    if len(companies) >= limit:
                        break
                    
                    try:
                        # Получаем URL страницы компании
                        company_url = self.base_url + link.get('href')
                        
                        # Парсим страницу компании
                        company_data = self._parse_company_page(company_url)
                        
                        if company_data:
                            # Проверяем сайт компании на наличие CAT-системы
                            if company_data.get('site'):
                                has_cat, evidence, product = check_website_for_cat(company_data['site'])
                                if has_cat:
                                    company_data['cat_evidence'] = evidence
                                    if product:
                                        company_data['cat_product'] = product
                                    company_data['source'] = 'zachestnyibiznes'
                                    companies.append(company_data)
                    except Exception as e:
                        print(f"      Ошибка при парсинге компании: {e}")
                        continue
                        
            except Exception as e:
                print(f"   Ошибка при поиске '{search_query}': {e}")
                continue
        
        return companies
    
    def _parse_company_page(self, url: str) -> Dict:
        """
        Парсит страницу компании на zachestnyibiznes.ru.
        
        Извлекает: ИНН, название, выручку, сайт, сотрудников, ОКВЭД.
        """
        try:
            response = self.make_request(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            company_data = {}
            
            # Извлекаем ИНН
            inn_elem = soup.find('td', string=re.compile(r'ИНН'))
            if inn_elem:
                inn_next = inn_elem.find_next_sibling('td')
                if inn_next:
                    company_data['inn'] = normalize_inn(inn_next.get_text(strip=True))
            
            # Альтернативный способ поиска ИНН
            if not company_data.get('inn'):
                inn_match = re.search(r'ИНН[:\s]+(\d{10,12})', soup.get_text())
                if inn_match:
                    company_data['inn'] = normalize_inn(inn_match.group(1))
            
            # Извлекаем название
            name_elem = soup.find('h1')
            if not name_elem:
                name_elem = soup.find('div', class_=re.compile(r'company-name|org-name'))
            if name_elem:
                company_data['name'] = name_elem.get_text(strip=True)
            
            # Извлекаем выручку
            revenue_elem = soup.find('td', string=re.compile(r'Выручка|Доход|Оборот'))
            if revenue_elem:
                revenue_next = revenue_elem.find_next_sibling('td')
                if revenue_next:
                    revenue_text = revenue_next.get_text(strip=True)
                    company_data['revenue'] = normalize_revenue(revenue_text)
            
            # Альтернативный способ поиска выручки
            if not company_data.get('revenue'):
                revenue_match = re.search(r'Выручка[:\s]+([\d\s,\.]+)', soup.get_text())
                if revenue_match:
                    company_data['revenue'] = normalize_revenue(revenue_match.group(1))
            
            # Извлекаем сайт
            site_elem = soup.find('a', href=re.compile(r'^https?://'))
            if site_elem:
                site_href = site_elem.get('href', '')
                if site_href and not site_href.startswith(self.base_url):
                    company_data['site'] = site_href
            
            # Альтернативный способ поиска сайта
            if not company_data.get('site'):
                site_elem = soup.find('td', string=re.compile(r'Сайт|Website'))
                if site_elem:
                    site_next = site_elem.find_next_sibling('td')
                    if site_next:
                        site_link = site_next.find('a')
                        if site_link:
                            company_data['site'] = site_link.get('href', '')
            
            # Извлекаем количество сотрудников
            employees_elem = soup.find('td', string=re.compile(r'Сотрудников|Работников|Численность'))
            if employees_elem:
                employees_next = employees_elem.find_next_sibling('td')
                if employees_next:
                    employees_text = employees_next.get_text(strip=True)
                    employees_num = re.sub(r'[^\d]', '', employees_text)
                    if employees_num:
                        try:
                            company_data['employees'] = int(employees_num)
                        except:
                            pass
            
            # Извлекаем основной ОКВЭД
            okved_elem = soup.find('td', string=re.compile(r'ОКВЭД'))
            if okved_elem:
                okved_next = okved_elem.find_next_sibling('td')
                if okved_next:
                    okved_text = okved_next.get_text(strip=True)
                    okved_match = re.search(r'(\d{2}\.\d{2})', okved_text)
                    if okved_match:
                        company_data['okved_main'] = okved_match.group(1)
            
            # Проверяем, что есть минимально необходимые данные
            if company_data.get('inn') and company_data.get('name'):
                return company_data
            
            return None
            
        except Exception as e:
            print(f"      Ошибка при парсинге страницы {url}: {e}")
            return None

