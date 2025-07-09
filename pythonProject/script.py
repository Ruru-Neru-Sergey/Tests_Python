import argparse
import csv
import sys
from tabulate import tabulate  # Для красивого вывода таблиц


def parse_condition(condition_str: str) -> tuple:
    """
    Разбирает строку условия фильтрации на компоненты.

    Args:
        condition_str: Строка условия в формате "колонка оператор значение"

    Returns:
        Кортеж (колонка, оператор, значение)

    Raises:
        ValueError: Если неверный формат условия
    """
    # Список поддерживаемых операторов в порядке проверки
    operators = ['>=', '<=', '>', '<', '==', '=']
    for op in operators:
        if op in condition_str:
            # Разделяем строку на колонку и значение
            parts = condition_str.split(op, 1)
            if len(parts) == 2:
                column = parts[0].strip()
                value_str = parts[1].strip()
                # Нормализуем оператор равенства
                if op == '=':
                    op = '=='
                return column, op, value_str
    raise ValueError(f"Неверный формат условия: {condition_str}")


def parse_aggregation(aggregation_str: str) -> tuple:
    """
    Разбирает строку агрегации на функцию и колонку.

    Args:
        aggregation_str: Строка агрегации в формате "функция=колонка"

    Returns:
        Кортеж (функция, колонка)

    Raises:
        ValueError: Если неверный формат или неподдерживаемая функция
    """
    if '=' not in aggregation_str:
        raise ValueError(f"Неверный формат агрегации: {aggregation_str}")

    # Разделяем на функцию и колонку
    func_name, column = aggregation_str.split('=', 1)
    func_name = func_name.strip().lower()
    column = column.strip()

    # Проверяем поддерживаемые функции
    if func_name not in ['avg', 'min', 'max']:
        raise ValueError(f"Неподдерживаемая функция агрегации: {func_name}")

    return func_name, column


def apply_filter(data: list, condition_str: str) -> list:
    """
    Применяет фильтрацию к данным по указанному условию.

    Args:
        data: Список словарей с данными
        condition_str: Строка условия фильтрации

    Returns:
        Отфильтрованный список данных
    """
    try:
        column, operator, value_str = parse_condition(condition_str)
    except ValueError as e:
        sys.exit(f"Ошибка: {e}")

    # Проверка существования колонки
    if column not in data[0]:
        sys.exit(f"Ошибка: Колонка '{column}' не найдена в CSV")

    # Преобразуем значение в число, если возможно
    try:
        # Пробуем преобразовать в float
        value = float(value_str)
    except ValueError:
        # Если не получается, оставляем строкой
        value = value_str

    filtered_data = []
    for row in data:
        cell_value = row[column]

        # Для числовых условий преобразуем значение ячейки
        if isinstance(value, float):
            try:
                cell_value = float(cell_value)
            except ValueError:
                # Если не числовое значение в числовой колонке
                sys.exit(f"Ошибка: Значение '{cell_value}' в колонке '{column}' не является числом")

        # Применяем оператор сравнения
        if operator == '>' and cell_value > value:
            filtered_data.append(row)
        elif operator == '<' and cell_value < value:
            filtered_data.append(row)
        elif operator == '>=' and cell_value >= value:
            filtered_data.append(row)
        elif operator == '<=' and cell_value <= value:
            filtered_data.append(row)
        elif operator == '==' and cell_value == value:
            filtered_data.append(row)

    return filtered_data


def apply_aggregation(data: list, aggregation_str: str) -> float:
    """
    Вычисляет агрегацию по указанной колонке.

    Args:
        data: Список словарей с данными
        aggregation_str: Строка агрегации в формате "функция=колонка"

    Returns:
        Результат вычисления (среднее, минимум или максимум)
    """
    try:
        func_name, column = parse_aggregation(aggregation_str)
    except ValueError as e:
        sys.exit(f"Ошибка: {e}")

    # Проверка существования колонки
    if column not in data[0]:
        sys.exit(f"Ошибка: Колонка '{column}' не найдена в CSV")

    values = []
    for row in data:
        try:
            # Пытаемся преобразовать значение в число
            num_value = float(row[column])
            values.append(num_value)
        except ValueError:
            sys.exit(f"Ошибка: Значение '{row[column]}' в колонке '{column}' не является числом")

    # Обработка пустого списка значений
    if not values:
        return 0.0

    # Вычисляем запрошенную агрегацию
    if func_name == 'avg':
        return sum(values) / len(values)
    elif func_name == 'min':
        return min(values)
    elif func_name == 'max':
        return max(values)
    else:
        return 0.0  # Недостижимый код


def main():
    """Основная функция скрипта."""
    # 1. создание парсера командной строки
    parser = argparse.ArgumentParser(
        description='Обработка CSV-файлов с фильтрацией и агрегацией',
        epilog='Пример: python script.py products.csv --where "price>500"'
    )

    # Объявление обязательного агрумента 'file'
    parser.add_argument('file', help='products.csv')

    # Опциональные аргументы (с дефисами)
    parser.add_argument('--where', help='Условие фильтрации (например, "price>500")')
    parser.add_argument('--aggregate', help='Агрегация данных (например, "avg=rating")')

    # Разбор аргументов командной строки
    args = parser.parse_args()

    # Берём путь к файлу
    file_path = args.file

    # чтение файла по указанному пути
    try:
        # Открываем файл с указанным путем
        # newline='' - для корректной работы с разными ОС
        # encoding='utf-8' - для поддержки кириллицы и других символов
        with open(file_path, newline='', encoding='utf-8') as csvfile:

            # Создаем reader для чтения CSV как словарей
            # Первая строка автоматически считается заголовком
            reader = csv.DictReader(csvfile)

            # Преобразуем данные в список словарей
            # Каждый словарь = одна строка, ключи = названия колонок
            data = list(reader)

    # Обработка ошибок файла
    except FileNotFoundError:
        # Если файл не найден по указанному пути
        sys.exit(f"ОШИБКА: Файл '{file_path}' не найден! Проверьте путь.")
    except Exception as e:
        # Другие ошибки (нет прав доступа, поврежден файл и т.д.)
        sys.exit(f"ОШИБКА чтения файла: {e}")

    # Обработка случая пустого файла
    if not data:
        print("Файл не содержит данных")
        return

    # Применение фильтрации (если указана)
    filtered_data = data
    if args.where:
        filtered_data = apply_filter(filtered_data, args.where)

    # Вывод результатов агрегации или таблицы
    if args.aggregate:
        result = apply_aggregation(filtered_data, args.aggregate)
        func_name, column = parse_aggregation(args.aggregate)
        # Специальное форматирование для среднего значения
        if func_name == 'avg':
            print(f"{func_name}({column}): {result:.3f}")
        else:
            print(f"{func_name}({column}): {result}")
    else:
        # Вывод данных в виде таблицы
        print(tabulate(filtered_data, headers="keys", tablefmt="grid"))


if __name__ == "__main__":
    main()