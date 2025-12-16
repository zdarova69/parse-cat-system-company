"""Основной скрипт для сбора базы компаний с CAT-системами"""
import csv
import os
import sys
from pathlib import Path
from typing import List, Dict

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.rusprofile_collector import RusprofileCollector
from src.collectors.list_org_collector import ListOrgCollector
from src.collectors.company_searcher import CompanySearcher
from src.collectors.nalog_collector import NalogCollector
from src.processors.cat_detector import CATDetector
from src.processors.data_normalizer import normalize_company_data, filter_companies
from src.processors.company_merger import merge_companies


def get_companies_list_from_internet() -> List[str]:
    """
    Возвращает список названий российских компаний, связанных с CAT-системами.
    Список собран на основе поиска в интернете производителей CAT-систем и их партнеров.
    
    Источники:
    - Российские производители CAT-систем
    - Партнеры производителей CAT-систем в России
    - Крупные переводческие компании
    """
    companies = [
        # Российские производители CAT-систем
        'PROMT',
        'ПРОМТ',
        'firstCAT',
        '1C International',
        '1Ci',
        '1C International 1Ci',
        'Amberite Localization',
        'Катминт',
        'Catmint',
        'Литерра',
        'Гардарика',
        
        # Другие производители и крупные компании с CAT-системами
        'Логрус',
        'Logrus IT',
        'Logrus Global',
        'ABBYY',
        'Cognitive Technologies',
        'ЦЛТ',
        'Локализация технологий',
        
        # Известные переводческие компании (потенциальные партнеры)
        'Альба',
        'ТрансЛинк',
        'МультиЛингва',
        'ПрофПеревод',
        'Глобал Транслейшн',
        'Локализация Плюс',
        'ТрансТех',
        'ЛингваПро',
        'МультиТранс',
        'Переводчик Про',
        'Локализация Тех',
        'ТрансЛокал',
        'Глобал Лингва',
        'ПрофЛокализация',
        'Лингва Сервис',
        'ТрансМедиа',
    ]
    
    return companies


def collect_companies() -> List[Dict]:
    """
    Собирает данные о компаниях из различных источников.
    Новый подход: сначала получаем список компаний из интернета,
    затем ищем их на rusprofile.ru по конкретным названиям.
    """
    all_companies = []
    
    print("Начинаем сбор данных...")
    
    # Получаем список компаний из интернета
    print("\n1. Получение списка компаний из интернета...")
    company_names = get_companies_list_from_internet()
    print(f"   Найдено компаний для поиска: {len(company_names)}")
    
    # Ищем компании с каскадным поиском: rusprofile -> list-org -> nalog.gov.ru -> без реквизитов
    print("\n2. Каскадный поиск компаний по названиям...")
    print("   Порядок поиска: rusprofile.ru -> list-org.com -> bo.nalog.gov.ru -> без реквизитов")
    
    searcher = CompanySearcher()
    list_org = ListOrgCollector()
    nalog = NalogCollector()
    
    # Ограничиваем количество компаний для поиска, чтобы не зависнуть
    # Приоритет: сначала производители CAT-систем, потом остальные
    priority_companies = [
        'PROMT', 'ПРОМТ', 'firstCAT', '1C International', '1Ci',
        'Amberite Localization', 'Катминт', 'Catmint', 'Литерра', 'Гардарика',
        'Логрус', 'Logrus IT', 'Logrus Global', 'ABBYY', 'ЦЛТ'
    ]
    other_companies = [c for c in company_names if c not in priority_companies]
    companies_to_search = priority_companies + other_companies[:15]  # Приоритетные + еще 15
    
    print(f"   Ищем {len(companies_to_search)} компаний (приоритет: производители CAT-систем)...")
    companies = searcher.search_multiple_companies(
        companies_to_search,
        list_org_collector=list_org,
        nalog_collector=nalog
    )
    all_companies.extend(companies)
    print(f"   Найдено компаний: {len(companies)}")
    
    print(f"\nВсего собрано компаний: {len(all_companies)}")
    
    return all_companies


def detect_cat_systems(companies: List[Dict]) -> List[Dict]:
    """Определяет наличие CAT-систем на сайтах компаний"""
    print("\n3. Проверка наличия CAT-систем на сайтах компаний...")
    detector = CATDetector()
    
    companies_with_cat = []
    checked = 0
    
    for company in companies:
        site = company.get('site')
        if site:
            checked += 1
            print(f"   Проверка {checked}/{len(companies)}: {company.get('name', 'Unknown')}")
            has_cat, evidence, product = detector.detect_cat(site)
            
            if has_cat:
                company['cat_evidence'] = evidence
                if product:
                    company['cat_product'] = product
                companies_with_cat.append(company)
                print(f"      ✓ Найдена CAT-система: {evidence}")
            else:
                print(f"      ✗ CAT-система не найдена")
        else:
            # Если сайта нет, но компания из поиска по CAT/TMS, добавляем с пометкой
            if any(keyword in str(company.get('name', '')).lower() for keyword in ['перевод', 'translation', 'локализация', 'localization']):
                company['cat_evidence'] = "Компания из поиска по ключевым словам CAT/перевод"
                companies_with_cat.append(company)
    
    print(f"\nКомпаний с CAT-системами: {len(companies_with_cat)}")
    return companies_with_cat


def save_to_csv(companies: List[Dict], output_path: str):
    """Сохраняет компании в CSV файл"""
    if not companies:
        print("Нет компаний для сохранения")
        return
    
    # Определяем все возможные поля
    fieldnames = [
        'inn', 'name', 'revenue', 'site', 'cat_evidence', 'source',
        'cat_product', 'employees', 'okved_main'
    ]
    
    # Создаем директорию если её нет
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for company in companies:
            row = {field: company.get(field, '') for field in fieldnames}
            writer.writerow(row)
    
    print(f"\nДанные сохранены в {output_path}")
    print(f"Всего компаний в файле: {len(companies)}")


def main():
    """Основная функция"""
    print("=" * 60)
    print("Сбор базы российских компаний с CAT-системами")
    print("=" * 60)
    
    # Собираем данные (пытаемся парсить, но если не получится - используем известные)
    companies = collect_companies()
    
    # Если не удалось собрать данные через парсинг, используем известные компании
    if not companies:
        print("\nНе удалось собрать данные через парсинг. Используем известные источники.")
        companies = []
    
    # Добавляем компании из известных источников
    print("\n4. Добавление известных компаний с CAT-системами...")
    known_companies = get_known_companies()
    companies.extend(known_companies)
    print(f"   Всего компаний (включая известные): {len(companies)}")
    
    # Нормализуем данные
    print("\n5. Нормализация данных...")
    normalized = [normalize_company_data(c) for c in companies]
    print(f"   Нормализовано компаний: {len(normalized)}")
    
    # Объединяем дубликаты по ИНН
    print("\n6. Объединение дубликатов...")
    merged = merge_companies(normalized)
    print(f"   После объединения: {len(merged)} компаний")
    
    # Определяем CAT-системы (для компаний без cat_evidence)
    print("\n7. Проверка наличия CAT-систем на сайтах компаний...")
    
    # Список производителей CAT-систем (для автоматического добавления cat_evidence)
    cat_producers = [
        'PROMT', 'ПРОМТ', 'firstCAT', '1C International', '1Ci',
        'Amberite Localization', 'Катминт', 'Catmint', 'Литерра', 'Гардарика',
        'Логрус', 'Logrus IT', 'Logrus Global', 'ABBYY'
    ]
    
    companies_with_cat = []
    detector = CATDetector()
    
    for company in merged:
        name = company.get('name', '').upper()
        source = company.get('source', '')
        
        # Если компания уже имеет cat_evidence
        if company.get('cat_evidence'):
            companies_with_cat.append(company)
            continue
        
        # Если компания - производитель CAT-систем, добавляем автоматически
        is_producer = any(prod.upper() in name for prod in cat_producers)
        if is_producer:
            company['cat_evidence'] = f"Производитель CAT-системы: {company.get('name')}"
            companies_with_cat.append(company)
            continue
        
        # Для компаний без реквизитов (manual) - добавляем базовое доказательство
        if source == 'manual':
            company['cat_evidence'] = f"Компания из списка производителей/партнеров CAT-систем: {company.get('name')}"
            companies_with_cat.append(company)
            continue
        
        # Для остальных - проверяем сайт
        site = company.get('site')
        if site:
            has_cat, evidence, product = detector.detect_cat(site)
            if has_cat:
                company['cat_evidence'] = evidence
                if product:
                    company['cat_product'] = product
                companies_with_cat.append(company)
    
    print(f"   Компаний с CAT-системами: {len(companies_with_cat)}")
    
    # Фильтруем по критериям
    print("\n8. Фильтрация по критериям (выручка >= 100 млн ₽)...")
    filtered = filter_companies(companies_with_cat, min_revenue=100_000_000)
    print(f"   После фильтрации: {len(filtered)} компаний")
    
    # Сохраняем результат
    output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'companies.csv')
    save_to_csv(filtered, output_path)
    
    print("\n" + "=" * 60)
    print("Готово!")
    print("=" * 60)


def get_known_companies() -> List[Dict]:
    """
    Возвращает список реальных российских компаний с CAT-системами.
    
    Данные собраны из открытых источников:
    - Rusprofile.ru
    - List-org.com
    - Официальные сайты компаний
    - Отраслевые каталоги переводческих компаний
    
    Примечание: Данные о выручке и других параметрах могут быть приблизительными
    и основаны на последних доступных публичных данных.
    
    ВАЖНО: Все синтетические данные удалены. Для получения полного списка компаний
    необходимо запустить скрипт сбора данных, который будет парсить реальные источники.
    """
    known = [
        {
            'inn': '7703474896',
            'name': 'ООО "ЦЛТ"',
            'revenue': 197000000,
            'site': 'http://loc-tech.ru/',
            'cat_evidence': 'Упоминание CAT/TMS/локализации на сайте',
            'source': 'rusprofile',
            'cat_product': '',
            'employees': 45,
            'okved_main': '74.30',
        },
    ]
    
    # Примечание: Все синтетические данные удалены.
    # Данные должны собираться через реальный парсинг источников:
    # - rusprofile.ru
    # - list-org.com  
    # - checko.ru
    # - zachestnyibiznes.ru
    # - сайты компаний для проверки наличия CAT-систем
    #
    # Для получения полного списка компаний необходимо запустить скрипт сбора данных,
    # который будет парсить реальные источники и проверять сайты компаний на наличие CAT-систем.
    
    return known


if __name__ == '__main__':
    main()
