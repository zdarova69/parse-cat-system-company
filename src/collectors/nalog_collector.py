"""Сборщик данных о выручке с bo.nalog.gov.ru по ИНН."""

import re
from typing import Optional, Dict
from bs4 import BeautifulSoup
from src.collectors.base_collector import BaseCollector
from src.utils.helpers import normalize_revenue, normalize_inn


class NalogCollector(BaseCollector):
    """Сборщик данных о выручке с bo.nalog.gov.ru по ИНН."""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://bo.nalog.gov.ru"
    
    def get_revenue_by_inn(self, inn: str) -> Optional[int]:
        """
        Получает выручку компании по ИНН с сайта bo.nalog.gov.ru.
        
        Args:
            inn: ИНН компании (10 или 12 цифр)
            
        Returns:
            Выручка в рублях (int) или None, если не найдено
        """
        inn_normalized = normalize_inn(inn)
        if not inn_normalized:
            return None
        
        try:
            # Формируем URL для поиска компании по ИНН
            search_url = f"{self.base_url}/search?query={inn_normalized}"
            
            # Выполняем запрос
            response = self.make_request(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем ссылку на страницу компании
            company_link = soup.find('a', href=re.compile(r'/company/\d+'))
            if not company_link:
                # Пробуем другой формат ссылки
                company_link = soup.find('a', href=re.compile(r'/ul/\d+'))
            
            if not company_link:
                return None
            
            # Получаем URL страницы компании
            company_url = self.base_url + company_link.get('href')
            
            # Парсим страницу компании
            return self._parse_company_revenue(company_url, inn_normalized)
            
        except Exception as e:
            print(f"      Ошибка при получении выручки для ИНН {inn_normalized}: {e}")
            return None
    
    def _parse_company_revenue(self, url: str, inn: str) -> Optional[int]:
        """
        Парсит страницу компании на bo.nalog.gov.ru и извлекает выручку.
        
        Args:
            url: URL страницы компании
            inn: ИНН для проверки
            
        Returns:
            Выручка в рублях (int) или None
        """
        try:
            response = self.make_request(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем выручку в финансовых показателях
            # На сайте ФНС данные могут быть в таблицах или списках
            
            # Способ 1: Ищем по тексту "Выручка"
            revenue_elem = soup.find('td', string=re.compile(r'Выручка', re.IGNORECASE))
            if revenue_elem:
                revenue_next = revenue_elem.find_next_sibling('td')
                if revenue_next:
                    revenue_text = revenue_next.get_text(strip=True)
                    revenue = normalize_revenue(revenue_text)
                    if revenue:
                        return revenue
            
            # Способ 2: Ищем в таблице финансовых показателей
            # Ищем таблицу с финансовыми данными
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        first_cell = cells[0].get_text(strip=True).lower()
                        if 'выручка' in first_cell or 'доход' in first_cell or 'оборот' in first_cell:
                            revenue_text = cells[1].get_text(strip=True)
                            revenue = normalize_revenue(revenue_text)
                            if revenue:
                                return revenue
            
            # Способ 3: Ищем по регулярному выражению в тексте страницы
            page_text = soup.get_text()
            revenue_patterns = [
                r'Выручка[:\s]+([\d\s,\.]+)',
                r'Доход[:\s]+([\d\s,\.]+)',
                r'Оборот[:\s]+([\d\s,\.]+)',
            ]
            
            for pattern in revenue_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    revenue = normalize_revenue(match)
                    if revenue:
                        return revenue
            
            return None
            
        except Exception as e:
            print(f"      Ошибка при парсинге страницы {url}: {e}")
            return None
    
    def enrich_company_revenue(self, company: Dict) -> Dict:
        """
        Обогащает данные компании выручкой с bo.nalog.gov.ru, если её нет или нужно проверить.
        
        Args:
            company: Словарь с данными компании
            
        Returns:
            Обогащенный словарь с данными компании
        """
        inn = company.get('inn')
        if not inn:
            return company
        
        # Если выручка уже есть и достаточная, можно не проверять
        existing_revenue = company.get('revenue')
        if existing_revenue and isinstance(existing_revenue, (int, float)) and existing_revenue >= 100_000_000:
            return company
        
        # Получаем выручку с сайта ФНС
        revenue_from_nalog = self.get_revenue_by_inn(inn)
        if revenue_from_nalog:
            # Используем выручку с ФНС, если она больше или если исходной не было
            if not existing_revenue or (isinstance(revenue_from_nalog, (int, float)) and revenue_from_nalog > existing_revenue):
                company['revenue'] = revenue_from_nalog
                # Обновляем источник, если выручка взята с ФНС
                existing_source = company.get('source', '')
                if 'nalog.gov.ru' not in existing_source:
                    company['source'] = f"{existing_source}, nalog.gov.ru" if existing_source else "nalog.gov.ru"
        
        return company

