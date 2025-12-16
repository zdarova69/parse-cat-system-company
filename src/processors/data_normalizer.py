"""Нормализация данных компаний"""
from typing import List, Dict, Optional
from src.utils.helpers import normalize_revenue, normalize_inn, normalize_url


def normalize_company_data(company: Dict) -> Dict:
    """Нормализует данные одной компании"""
    normalized = {
        'inn': normalize_inn(company.get('inn')),
        'name': company.get('name', '').strip() if company.get('name') else '',
        'revenue': normalize_revenue(company.get('revenue')),
        'site': normalize_url(company.get('site')),
        'cat_evidence': company.get('cat_evidence', '').strip(),
        'source': company.get('source', '').strip(),
        'cat_product': company.get('cat_product', '').strip() if company.get('cat_product') else '',
        'employees': company.get('employees'),
        'okved_main': company.get('okved_main', '').strip() if company.get('okved_main') else '',
    }
    
    return normalized


def filter_companies(companies: List[Dict], min_revenue: int = 100_000_000) -> List[Dict]:
    """
    Фильтрует компании по критериям:
    - Россия (проверка по ИНН: 10 или 12 цифр, или source='manual' для компаний без реквизитов)
    - Выручка >= min_revenue (или отсутствует, если source='manual' или производитель CAT-систем)
    - Наличие cat_evidence
    """
    filtered = []
    
    # Список производителей CAT-систем (для них выручка не обязательна)
    cat_producers_keywords = [
        'PROMT', 'ПРОМТ', 'firstCAT', '1C International', '1Ci',
        'Amberite', 'Катминт', 'Catmint', 'Литерра', 'Гардарика',
        'Логрус', 'ABBYY'
    ]
    
    for company in companies:
        source = company.get('source', '')
        name = company.get('name', '').upper()
        
        # Проверка наличия доказательства CAT
        if not company.get('cat_evidence'):
            continue
        
        # Для компаний без реквизитов (manual) - более мягкие критерии
        if source == 'manual':
            filtered.append(company)
            continue
        
        # Проверка ИНН (российский формат)
        inn = company.get('inn')
        if not inn or len(str(inn)) not in [10, 12]:
            continue
        
        # Проверка выручки
        revenue = company.get('revenue')
        
        # Для производителей CAT-систем выручка не обязательна
        is_producer = any(prod.upper() in name for prod in cat_producers_keywords)
        
        if revenue and revenue >= min_revenue:
            # Выручка >= 100 млн - добавляем
            filtered.append(company)
        elif is_producer:
            # Производитель CAT-систем - добавляем даже без выручки
            filtered.append(company)
        # Для остальных - пропускаем, если выручка < 100 млн
    
    return filtered

