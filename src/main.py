"""Основной скрипт для сбора компаний с CAT-системами."""

import os
import sys
import csv
from pathlib import Path
from typing import List, Dict

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.rusprofile_collector import RusprofileCollector
from src.collectors.list_org_collector import ListOrgCollector
from src.collectors.zachestnyibiznes_collector import ZachestnyibiznesCollector
from src.collectors.checko_collector import CheckoCollector
from src.processors.data_normalizer import filter_companies
from src.processors.company_merger import merge_companies_by_inn


def collect_companies_from_sources() -> List[Dict]:
    """Собирает компании из всех доступных источников."""
    all_companies = []
    
    print("Начало сбора данных...")
    
    # Сбор с rusprofile.ru (парсинг интернета)
    print("\n1. Парсинг rusprofile.ru...")
    try:
        rusprofile = RusprofileCollector()
        companies = rusprofile.collect(limit=50)
        all_companies.extend(companies)
        print(f"   Собрано {len(companies)} компаний с rusprofile")
    except Exception as e:
        print(f"   Ошибка при парсинге rusprofile: {e}")
    
    # Сбор с list-org.com (парсинг интернета)
    print("\n2. Парсинг list-org.com...")
    try:
        list_org = ListOrgCollector()
        companies = list_org.collect(limit=50)
        all_companies.extend(companies)
        print(f"   Собрано {len(companies)} компаний с list-org")
    except Exception as e:
        print(f"   Ошибка при парсинге list-org: {e}")
    
    # Сбор с zachestnyibiznes.ru (парсинг интернета)
    print("\n3. Парсинг zachestnyibiznes.ru...")
    try:
        zachestnyibiznes = ZachestnyibiznesCollector()
        companies = zachestnyibiznes.collect(limit=50)
        all_companies.extend(companies)
        print(f"   Собрано {len(companies)} компаний с zachestnyibiznes")
    except Exception as e:
        print(f"   Ошибка при парсинге zachestnyibiznes: {e}")
    
    # Сбор с checko.ru (парсинг интернета)
    print("\n4. Парсинг checko.ru...")
    try:
        checko = CheckoCollector()
        companies = checko.collect(limit=50)
        all_companies.extend(companies)
        print(f"   Собрано {len(companies)} компаний с checko")
    except Exception as e:
        print(f"   Ошибка при парсинге checko: {e}")
    
    return all_companies




def save_to_csv(companies: List[Dict], output_path: str):
    """Сохраняет компании в CSV файл."""
    if not companies:
        print("Нет компаний для сохранения!")
        return
    
    # Определяем названия полей
    fieldnames = [
        'inn', 'name', 'revenue', 'site', 'cat_evidence', 'source',
        'cat_product', 'employees', 'okved_main'
    ]
    
    # Создаем выходную директорию, если её нет
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for company in companies:
            # Убеждаемся, что все поля присутствуют
            row = {field: company.get(field, '') for field in fieldnames}
            writer.writerow(row)
    
    print(f"\nСохранено {len(companies)} компаний в {output_path}")


def main():
    """Основная функция выполнения."""
    print("=" * 60)
    print("Сбор данных о компаниях с CAT-системами")
    print("=" * 60)
    
    # Собираем компании из интернета
    companies = collect_companies_from_sources()
    
    print(f"\nВсего собрано компаний (до объединения): {len(companies)}")
    
    # Объединяем данные о компаниях по ИНН из разных источников
    print("\nОбъединение данных о компаниях из разных источников по ИНН...")
    merged_companies = merge_companies_by_inn(companies)
    print(f"Уникальных компаний после объединения: {len(merged_companies)}")
    
    # Фильтруем и нормализуем
    print("\nФильтрация и нормализация данных...")
    filtered = filter_companies(merged_companies, min_revenue=100_000_000)
    print(f"После фильтрации (выручка >= 100М): {len(filtered)}")
    
    # Сохраняем в CSV
    output_path = os.path.join('data', 'companies.csv')
    save_to_csv(filtered, output_path)
    
    # Выводим итоги
    print("\n" + "=" * 60)
    print("Итоги:")
    print(f"  Всего компаний собрано (до объединения): {len(companies)}")
    print(f"  Уникальных компаний после объединения: {len(merged_companies)}")
    print(f"  Компаний после фильтрации: {len(filtered)}")
    print(f"  Выходной файл: {output_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()

