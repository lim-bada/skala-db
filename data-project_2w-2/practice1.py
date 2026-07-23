"""
프로그램명: 실습 1 - Python 자료구조 집계 및 제너레이터
작성자: 임해안
작성일: 2026-07-20

목적:
    Python_Practice2_Data.json의 판매 데이터를 이용해 컴프리헨션,
    Counter, defaultdict, 제너레이터 기반의 집계 결과를 확인한다.

입력 데이터:
    region, category, amount, month 키를 가진 거래 목록(JSON)

변경 이력:
    - 2026-07-20: 실습 1의 1~4번 구현 및 결과 검증 추가
    - 2026-07-20: Practice2 JSON 파일 적용, 예외 처리와 데이터 검증 보강
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


DATA_FILE = Path("Python_Practice2_Data.json")
REQUIRED_KEYS = ("region", "category", "amount", "month")

EXPECTED_REGION_TOTAL = {
    "서울": 17670,
    "부산": 4550,
    "대구": 8320,
    "인천": 11950,
    "광주": 4830,
    "대전": 6300,
    "울산": 7270,
    "세종": 5750,
}
EXPECTED_REGION_COUNT = {
    "서울": 14,
    "부산": 13,
    "대구": 13,
    "인천": 12,
    "광주": 12,
    "대전": 12,
    "울산": 12,
    "세종": 12,
}
EXPECTED_CATEGORY_COUNT = {"전자": 39, "의류": 34, "식품": 27}
EXPECTED_MONTHLY_CATEGORY_SALES = {
    "2024-01": {"전자": 12030, "의류": 8350, "식품": 2730},
    "2024-02": {"전자": 15240, "의류": 7720, "식품": 3910},
    "2024-03": {"전자": 13820, "의류": 7960, "식품": 2510},
    "2024-04": {"전자": 14010, "의류": 9190, "식품": 3990},
}


def validate_sales_data(sales):
    """JSON 데이터의 최상위 구조, 필수 키, 필드 자료형을 검증한다."""
    if not isinstance(sales, list):
        raise ValueError("JSON 최상위 구조는 거래 목록(list)이어야 합니다.")

    for index, sale in enumerate(sales, start=1):
        if not isinstance(sale, dict):
            raise TypeError(f"{index}번째 거래가 딕셔너리(dict)가 아닙니다.")

        missing_keys = [key for key in REQUIRED_KEYS if key not in sale]
        if missing_keys:
            raise KeyError(f"{index}번째 거래에 필수 키가 없습니다: {missing_keys}")

        for key in ("region", "category", "month"):
            if not isinstance(sale[key], str) or not sale[key].strip():
                raise TypeError(f"{index}번째 거래의 {key} 값은 빈 문자열이 아닌 문자열이어야 합니다.")

        amount = sale["amount"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError(f"{index}번째 거래의 amount 값은 숫자여야 합니다.")


def load_sales_data(data_file):
    """JSON 파일을 읽고, 분석 전에 데이터 형식이 올바른지 확인한다."""
    with data_file.open("r", encoding="utf-8") as file:
        sales = json.load(file)

    validate_sales_data(sales)
    return sales


def high_value_sales_generator(sales):
    """amount가 1000보다 큰 거래를 한 건씩 생성해 메모리 사용을 줄인다."""
    for sale in sales:
        if sale["amount"] > 1000:
            yield sale


def run_comprehension_practice(sales):
    """실습 1-1: 조건 필터링과 지역별 총매출을 컴프리헨션으로 계산한다."""
    print("\n[실습 1-1] 리스트/딕셔너리 컴프리헨션")

    filtered_sales = [sale for sale in sales if sale["amount"] >= 1000]
    regions = sorted({sale["region"] for sale in filtered_sales})
    region_total = {
        region: sum(sale["amount"] for sale in filtered_sales if sale["region"] == region)
        for region in regions
    }

    print("1000 이상 거래 수:", len(filtered_sales))
    print("1000 이상 거래 목록:")
    for sale in filtered_sales:
        print(sale)
    print("\n지역별 총매출:")
    print(region_total)

    assert region_total == EXPECTED_REGION_TOTAL, "지역별 총매출이 기대값과 다릅니다."


def run_counter_defaultdict_practice(sales):
    """실습 1-2: Counter와 defaultdict로 거래 건수와 금액 목록을 집계한다."""
    print("\n[실습 1-2] Counter + defaultdict")

    region_count = Counter(sale["region"] for sale in sales)
    category_amounts = defaultdict(list)
    for sale in sales:
        category_amounts[sale["category"]].append(sale["amount"])

    print("지역별 거래 건수:")
    print(region_count)
    print("\n거래 건수 내림차순:")
    print(region_count.most_common())
    print("\n카테고리별 amount 목록:")
    for category, amounts in category_amounts.items():
        print(f"{category}: {amounts}")

    category_count = {
        category: len(amounts)
        for category, amounts in category_amounts.items()
    }
    assert region_count == Counter(EXPECTED_REGION_COUNT), "지역별 거래 건수가 기대값과 다릅니다."
    assert region_count.most_common(3) == [
        ("서울", 14),
        ("부산", 13),
        ("대구", 13),
    ], "Counter.most_common(3) 결과가 기대값과 다릅니다."
    assert category_count == EXPECTED_CATEGORY_COUNT, "카테고리별 거래 건수가 기대값과 다릅니다."


def run_generator_practice(sales):
    """실습 1-3: 같은 결과의 리스트와 제너레이터 객체 메모리를 비교한다."""
    print("\n[실습 1-3] 제너레이터 메모리 비교")

    high_value_sales_list = [sale for sale in sales if sale["amount"] > 1000]
    high_value_sales = high_value_sales_generator(sales)
    list_memory_size = sys.getsizeof(high_value_sales_list)
    generator_memory_size = sys.getsizeof(high_value_sales)

    print("amount > 1000 거래 수:", len(high_value_sales_list))
    print("리스트 메모리 크기:", list_memory_size, "bytes")
    print("제너레이터 메모리 크기:", generator_memory_size, "bytes")

    assert generator_memory_size < list_memory_size, (
        "제너레이터의 메모리 크기가 리스트보다 작아야 합니다."
    )


def run_grouping_practice(sales):
    """실습 1-4: 월·카테고리 매출과 금액 기준 상위 3개 거래를 집계한다."""
    print("\n[실습 1-4] 월별 카테고리 매출 집계 및 금액 Top 3")

    month_category_totals = defaultdict(lambda: defaultdict(int))
    for sale in sales:
        month_category_totals[sale["month"]][sale["category"]] += sale["amount"]

    monthly_category_sales = {
        month: dict(month_category_totals[month])
        for month in sorted(month_category_totals)
    }
    top3_sales_by_amount = sorted(
        sales,
        key=lambda sale: sale["amount"],
        reverse=True,
    )[:3]
    top3_amounts = [sale["amount"] for sale in top3_sales_by_amount]

    print("월별 카테고리 총매출:")
    for month, category_totals in monthly_category_sales.items():
        print(f"{month}: {category_totals}")
    print("\n금액 기준 상위 3개 거래:")
    for sale in top3_sales_by_amount:
        print(sale)

    assert monthly_category_sales == EXPECTED_MONTHLY_CATEGORY_SALES, (
        "월별 카테고리 총매출이 기대값과 다릅니다."
    )
    assert top3_amounts == [2500, 2200, 2200], "금액 상위 3개 결과가 기대값과 다릅니다."
    assert top3_amounts == sorted(top3_amounts, reverse=True), (
        "금액 상위 3개가 내림차순으로 정렬되지 않았습니다."
    )


def main():
    """실습 1의 모든 항목을 실행하고, 오류 발생 시 원인을 안내한다."""
    try:
        sales = load_sales_data(DATA_FILE)
        run_comprehension_practice(sales)
        run_counter_defaultdict_practice(sales)
        run_generator_practice(sales)
        run_grouping_practice(sales)
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {DATA_FILE}")
        return 1
    except PermissionError:
        print(f"파일을 읽을 권한이 없습니다: {DATA_FILE}")
        return 1
    except UnicodeDecodeError:
        print("파일 인코딩을 UTF-8로 읽을 수 없습니다.")
        return 1
    except json.JSONDecodeError as error:
        print("JSON 파일 형식이 올바르지 않습니다.")
        print(f"오류 위치: {error.lineno}행 {error.colno}열")
        return 1
    except (KeyError, TypeError, ValueError) as error:
        print(f"데이터 구조 또는 값이 올바르지 않습니다: {error}")
        return 1
    except OSError as error:
        print(f"파일 처리 중 운영체제 오류가 발생했습니다: {error}")
        return 1
    except AssertionError as error:
        print(f"결과 검증에 실패했습니다: {error}")
        return 1

    print("\n실습 1의 1~4번 검증을 모두 통과했습니다!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
