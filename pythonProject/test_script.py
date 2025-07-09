import os
import csv
import pytest
import tempfile
import sys
from unittest.mock import patch
from script import parse_condition, parse_aggregation, apply_filter, apply_aggregation, main


# Фикстура для тестовых данных
@pytest.fixture
def sample_data():
    return [
        {"name": "iphone 15 pro", "brand": "apple", "price": "999", "rating": "4.9"},
        {"name": "galaxy s23 ultra", "brand": "samsung", "price": "1199", "rating": "4.8"},
        {"name": "redmi note 12", "brand": "xiaomi", "price": "199", "rating": "4.6"},
        {"name": "poco x5 pro", "brand": "xiaomi", "price": "299", "rating": "4.4"},
    ]


# Фикстура для временного CSV-файла
@pytest.fixture
def temp_csv(sample_data):
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["name", "brand", "price", "rating"])
        writer.writeheader()
        writer.writerows(sample_data)
        f.flush()
        yield f.name
    os.unlink(f.name)


# Тесты для разбора условий
def test_parse_condition():
    assert parse_condition("price>500") == ("price", ">", "500")
    assert parse_condition("brand==apple") == ("brand", "==", "apple")
    assert parse_condition("rating>=4.5") == ("rating", ">=", "4.5")
    assert parse_condition("price<=1000") == ("price", "<=", "1000")


def test_parse_condition_errors():
    with pytest.raises(ValueError):
        parse_condition("price")  # Нет оператора

    with pytest.raises(ValueError):
        parse_condition("price>>500")  # Неверный оператор


# Тесты для разбора агрегации
def test_parse_aggregation():
    assert parse_aggregation("avg=price") == ("avg", "price")
    assert parse_aggregation("min=rating") == ("min", "rating")
    assert parse_aggregation("max=price") == ("max", "price")


def test_parse_aggregation_errors():
    with pytest.raises(ValueError):
        parse_aggregation("sum=price")  # Неподдерживаемая функция

    with pytest.raises(ValueError):
        parse_aggregation("avg")  # Нет знака равенства


# Тесты фильтрации
def test_apply_filter(sample_data):
    # Фильтр по цене
    result = apply_filter(sample_data, "price>500")
    assert len(result) == 2
    assert result[0]["name"] == "iphone 15 pro"
    assert result[1]["name"] == "galaxy s23 ultra"

    # Фильтр по бренду
    result = apply_filter(sample_data, "brand==xiaomi")
    assert len(result) == 2
    assert result[0]["name"] == "redmi note 12"
    assert result[1]["name"] == "poco x5 pro"

    # Фильтр по рейтингу
    result = apply_filter(sample_data, "rating>=4.5")
    assert len(result) == 3


def test_apply_filter_errors(sample_data):
    # Несуществующая колонка
    with pytest.raises(SystemExit):
        apply_filter(sample_data, "invalid>500")

    # Некорректное условие
    with pytest.raises(SystemExit):
        apply_filter(sample_data, "price>>500")


# Тесты агрегации
def test_apply_aggregation(sample_data):
    # Средняя цена
    result = apply_aggregation(sample_data, "avg=price")
    assert round(result, 2) == 674.00

    # Минимальный рейтинг
    result = apply_aggregation(sample_data, "min=rating")
    assert result == 4.4

    # Максимальная цена
    result = apply_aggregation(sample_data, "max=price")
    assert result == 1199.0


def test_apply_aggregation_errors(sample_data):
    # Несуществующая колонка
    with pytest.raises(SystemExit):
        apply_aggregation(sample_data, "avg=invalid")

    # Нечисловая колонка
    with pytest.raises(SystemExit):
        apply_aggregation(sample_data, "avg=name")


# Тесты комбинированных операций
def test_combined_operations(sample_data):
    # Фильтр + агрегация
    filtered = apply_filter(sample_data, "brand==xiaomi")
    result = apply_aggregation(filtered, "min=price")
    assert result == 199.0

    # Фильтр + агрегация по пустым данным
    filtered = apply_filter(sample_data, "price>2000")
    result = apply_aggregation(filtered, "avg=price")
    assert result == 0.0


# Тесты для всех операторов
def test_all_operators(sample_data):
    assert len(apply_filter(sample_data, "price>500")) == 2
    assert len(apply_filter(sample_data, "price<500")) == 2
    assert len(apply_filter(sample_data, "price>=999")) == 2
    assert len(apply_filter(sample_data, "price<=199")) == 1
    assert len(apply_filter(sample_data, "brand==apple")) == 1


# Тесты обработки ошибок
def test_invalid_condition(sample_data):
    with pytest.raises(SystemExit):
        apply_filter(sample_data, "invalid>condition")


def test_invalid_aggregation(sample_data):
    with pytest.raises(SystemExit):
        apply_aggregation(sample_data, "sum=price")


# Тесты функции main
def test_main_full_output(capsys, temp_csv):
    # Весь файл
    with patch.object(sys, 'argv', ['script', temp_csv]):
        main()
    captured = capsys.readouterr()
    assert "iphone 15 pro" in captured.out
    assert "galaxy s23 ultra" in captured.out


def test_main_filter(capsys, temp_csv):
    # Фильтр по цене
    with patch.object(sys, 'argv', ['script', temp_csv, '--where', 'price>500']):
        main()
    captured = capsys.readouterr()
    assert "iphone 15 pro" in captured.out
    assert "galaxy s23 ultra" in captured.out
    assert "redmi note 12" not in captured.out


def test_main_aggregation(capsys, temp_csv):
    # Агрегация
    with patch.object(sys, 'argv', ['script', temp_csv, '--aggregate', 'avg=price']):
        main()
    captured = capsys.readouterr()
    assert "avg(price): 674.000" in captured.out


def test_main_combined(capsys, temp_csv):
    # Фильтр + агрегация
    with patch.object(sys, 'argv', ['script', temp_csv, '--where', 'brand==xiaomi', '--aggregate', 'max=price']):
        main()
    captured = capsys.readouterr()
    assert "max(price): 299" in captured.out


def test_main_nonexistent_file(capsys):
    # Несуществующий файл
    with patch.object(sys, 'argv', ['script', 'nonexistent.csv']):
        main()
    captured = capsys.readouterr()
    assert "не найден" in captured.out or "not found" in captured.out


def test_main_empty_file(capsys, tmp_path):
    # Пустой файл
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding='utf-8')

    with patch.object(sys, 'argv', ['script', str(empty_file)]):
        main()
    captured = capsys.readouterr()
    assert "не содержит данных" in captured.out or "No data" in captured.out


def test_main_non_numeric_aggregation(capsys, temp_csv):
    # Агрегация по нечисловой колонке
    with patch.object(sys, 'argv', ['script', temp_csv, '--aggregate', 'avg=name']):
        main()
    captured = capsys.readouterr()
    assert "не является числом" in captured.out or "not a number" in captured.out


def test_main_invalid_encoding(capsys, tmp_path):
    # Файл с неверной кодировкой
    bad_file = tmp_path / "bad.csv"
    bad_file.write_bytes(b"\xff\xfe")  # Невалидные байты

    with patch.object(sys, 'argv', ['script', str(bad_file)]):
        main()
    captured = capsys.readouterr()
    assert "ОШИБКА" in captured.out or "ERROR" in captured.out


# Тест для пустых данных после фильтрации
def test_empty_data_after_filter(sample_data):
    # Фильтр, который ничего не возвращает
    result = apply_filter(sample_data, "price>2000")
    assert len(result) == 0

    # Агрегация по пустым данным
    result = apply_aggregation(result, "avg=price")
    assert result == 0.0


# Тест для данных с одной строкой
def test_single_row_data():
    data = [{"name": "test", "price": "100", "rating": "4.0"}]
    assert apply_aggregation(data, "avg=price") == 100.0
    assert apply_aggregation(data, "min=price") == 100.0
    assert apply_aggregation(data, "max=price") == 100.0


# Тест для разных типов данных
def test_different_data_types():
    data = [
        {"int": "10", "float": "5.5", "str": "text", "bool": "True"},
    ]

    # Числовые типы
    assert apply_filter(data, "int>5")[0]["int"] == "10"
    assert apply_filter(data, "float<6")[0]["float"] == "5.5"

    # Строковые типы
    assert apply_filter(data, "str==text")[0]["str"] == "text"

    # Булевы значения
    assert apply_filter(data, "bool==True")[0]["bool"] == "True"