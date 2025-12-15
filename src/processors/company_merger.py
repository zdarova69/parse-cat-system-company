"""Модуль для объединения данных о компаниях из разных источников по ИНН."""

from typing import List, Dict, Optional
from src.utils.helpers import normalize_inn


def merge_companies_by_inn(companies: List[Dict]) -> List[Dict]:
    """
    Объединяет данные о компаниях из разных источников по ИНН.
    
    Если одна и та же компания (по ИНН) найдена на разных сайтах,
    объединяет данные, приоритезируя более полные источники.
    
    Args:
        companies: Список словарей с данными о компаниях из разных источников
        
    Returns:
        Список уникальных компаний с объединенными данными
    """
    # Словарь для хранения объединенных данных: ИНН -> данные компании
    merged_dict = {}
    
    for company in companies:
        inn = normalize_inn(company.get('inn', ''))
        if not inn:
            # Если нет ИНН, пропускаем (не можем объединить)
            continue
        
        if inn not in merged_dict:
            # Первая встреча компании с этим ИНН
            merged_dict[inn] = company.copy()
            # Храним список источников
            merged_dict[inn]['sources'] = [company.get('source', 'unknown')]
        else:
            # Объединяем данные с уже существующей записью
            existing = merged_dict[inn]
            new_source = company.get('source', 'unknown')
            
            # Объединяем источники
            if new_source not in existing.get('sources', []):
                if 'sources' not in existing:
                    existing['sources'] = [existing.get('source', 'unknown'), new_source]
                else:
                    existing['sources'].append(new_source)
            
            # Обновляем source - перечисляем все источники через запятую
            if 'sources' in existing:
                existing['source'] = ', '.join(existing['sources'])
            else:
                existing['source'] = existing.get('source', 'unknown')
            
            # Объединяем данные (приоритет существующим данным, если они не пустые)
            # Название - берем более полное
            if not existing.get('name') or (company.get('name') and len(company['name']) > len(existing.get('name', ''))):
                existing['name'] = company.get('name', existing.get('name'))
            
            # Выручка - берем большее значение (более свежее или точное)
            existing_revenue = existing.get('revenue')
            new_revenue = company.get('revenue')
            if isinstance(existing_revenue, (int, float)) and isinstance(new_revenue, (int, float)):
                if new_revenue > existing_revenue:
                    existing['revenue'] = new_revenue
            elif not existing_revenue and new_revenue:
                existing['revenue'] = new_revenue
            
            # Сайт - берем первый найденный (обычно они одинаковые)
            if not existing.get('site') and company.get('site'):
                existing['site'] = company['site']
            
            # Доказательство CAT - объединяем, если разное
            existing_evidence = existing.get('cat_evidence', '')
            new_evidence = company.get('cat_evidence', '')
            if new_evidence and new_evidence != existing_evidence:
                if existing_evidence:
                    existing['cat_evidence'] = f"{existing_evidence} | {new_evidence}"
                else:
                    existing['cat_evidence'] = new_evidence
            
            # CAT продукт - берем более конкретный
            if not existing.get('cat_product') or existing.get('cat_product') == 'Не указан':
                if company.get('cat_product') and company.get('cat_product') != 'Не указан':
                    existing['cat_product'] = company['cat_product']
            
            # Сотрудники - берем большее значение
            existing_employees = existing.get('employees')
            new_employees = company.get('employees')
            if isinstance(existing_employees, (int, float)) and isinstance(new_employees, (int, float)):
                if new_employees > existing_employees:
                    existing['employees'] = new_employees
            elif not existing_employees and new_employees:
                existing['employees'] = new_employees
            
            # ОКВЭД - берем существующий (обычно одинаковый)
            if not existing.get('okved_main') and company.get('okved_main'):
                existing['okved_main'] = company['okved_main']
            
            merged_dict[inn] = existing
    
    # Удаляем служебное поле sources перед возвратом
    result = []
    for inn, company in merged_dict.items():
        if 'sources' in company:
            del company['sources']
        result.append(company)
    
    return result


def enrich_company_from_other_sources(company: Dict, all_companies: List[Dict]) -> Dict:
    """
    Обогащает данные компании информацией из других источников.
    
    Ищет компанию по ИНН в списке всех компаний и объединяет данные.
    
    Args:
        company: Компания для обогащения
        all_companies: Список всех компаний из разных источников
        
    Returns:
        Обогащенная компания
    """
    inn = normalize_inn(company.get('inn', ''))
    if not inn:
        return company
    
    # Ищем дополнительные данные в других источниках
    for other_company in all_companies:
        other_inn = normalize_inn(other_company.get('inn', ''))
        if other_inn == inn and other_company.get('source') != company.get('source'):
            # Нашли ту же компанию из другого источника
            # Объединяем данные
            if not company.get('site') and other_company.get('site'):
                company['site'] = other_company['site']
            
            if not company.get('revenue') and other_company.get('revenue'):
                company['revenue'] = other_company['revenue']
            
            if not company.get('employees') and other_company.get('employees'):
                company['employees'] = other_company['employees']
            
            if not company.get('okved_main') and other_company.get('okved_main'):
                company['okved_main'] = other_company['okved_main']
            
            # Объединяем источники
            existing_source = company.get('source', '')
            other_source = other_company.get('source', '')
            if other_source not in existing_source:
                company['source'] = f"{existing_source}, {other_source}" if existing_source else other_source
    
    return company

