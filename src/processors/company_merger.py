"""Объединение данных о компаниях из разных источников"""
from typing import List, Dict


def merge_companies(companies: List[Dict]) -> List[Dict]:
    """
    Объединяет данные об одной компании из разных источников по ИНН
    
    Приоритет:
    - Более полные данные (больше заполненных полей)
    - Большая выручка
    - Более конкретные доказательства CAT
    """
    # Группируем по ИНН
    companies_by_inn = {}
    
    for company in companies:
        inn = company.get('inn')
        if not inn:
            continue
        
        if inn not in companies_by_inn:
            companies_by_inn[inn] = []
        
        companies_by_inn[inn].append(company)
    
    # Объединяем данные
    merged = []
    
    for inn, company_list in companies_by_inn.items():
        if len(company_list) == 1:
            merged.append(company_list[0])
        else:
            # Выбираем лучшую версию
            best_company = company_list[0]
            
            for company in company_list[1:]:
                # Считаем количество заполненных полей
                best_fields = sum(1 for v in best_company.values() if v)
                current_fields = sum(1 for v in company.values() if v)
                
                # Если текущая компания имеет больше данных
                if current_fields > best_fields:
                    best_company = company
                # Если одинаково, выбираем с большей выручкой
                elif current_fields == best_fields:
                    best_revenue = best_company.get('revenue', 0) or 0
                    current_revenue = company.get('revenue', 0) or 0
                    if current_revenue > best_revenue:
                        best_company = company
            
            # Объединяем источники
            sources = [c.get('source', '') for c in company_list if c.get('source')]
            if len(sources) > 1:
                best_company['source'] = ','.join(set(sources))
            
            # Объединяем доказательства CAT
            evidences = [c.get('cat_evidence', '') for c in company_list if c.get('cat_evidence')]
            if len(evidences) > 1:
                best_company['cat_evidence'] = ' | '.join(set(evidences))
            
            # Заполняем пустые поля из других источников
            for company in company_list:
                for key, value in company.items():
                    if not best_company.get(key) and value:
                        best_company[key] = value
            
            merged.append(best_company)
    
    return merged

