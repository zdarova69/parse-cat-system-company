"""Модуль для нормализации и очистки данных о компаниях."""

from typing import Dict, Optional
from src.utils.helpers import normalize_revenue, normalize_inn, normalize_name


def normalize_company_data(company: Dict) -> Dict:
    """
    Нормализует данные компании к стандартному формату.
    
    Ожидаемые входные поля:
    - inn, name, revenue, site, cat_evidence, source
    - Опционально: cat_product, employees, okved_main
    """
    normalized = {}
    
    # Обязательные поля
    normalized['inn'] = normalize_inn(company.get('inn', ''))
    normalized['name'] = normalize_name(company.get('name', ''))
    
    # Выручка - должно быть целое число >= 100,000,000
    revenue_raw = company.get('revenue', '')
    if isinstance(revenue_raw, str):
        normalized['revenue'] = normalize_revenue(revenue_raw)
    elif isinstance(revenue_raw, (int, float)):
        normalized['revenue'] = int(revenue_raw)
    else:
        normalized['revenue'] = None
    
    # Сайт - нормализуем URL
    site = company.get('site', '').strip()
    if site and not site.startswith(('http://', 'https://')):
        site = 'https://' + site
    normalized['site'] = site
    
    # Доказательство - очищаем
    normalized['cat_evidence'] = company.get('cat_evidence', '').strip()
    normalized['source'] = company.get('source', '').strip()
    
    # Опциональные поля
    normalized['cat_product'] = company.get('cat_product', '').strip() or None
    normalized['employees'] = company.get('employees')
    if normalized['employees']:
        try:
            normalized['employees'] = int(str(normalized['employees']).replace(' ', '').replace(',', ''))
        except:
            normalized['employees'] = None
    else:
        normalized['employees'] = None
    
    normalized['okved_main'] = company.get('okved_main', '').strip() or None
    
    return normalized


def filter_companies(companies: list, min_revenue: int = 100_000_000) -> list:
    """
    Фильтрует компании по критериям:
    - Должен быть ИНН
    - Должно быть название
    - Выручка >= min_revenue
    - Должно быть доказательство использования CAT-системы
    """
    filtered = []
    
    for company in companies:
        normalized = normalize_company_data(company)
        
        # Проверяем обязательные поля
        if not normalized.get('inn'):
            continue
        
        if not normalized.get('name'):
            continue
        
        if not normalized.get('revenue') or normalized['revenue'] < min_revenue:
            continue
        
        if not normalized.get('cat_evidence'):
            continue
        
        filtered.append(normalized)
    
    return filtered



