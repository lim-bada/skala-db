"""
프로그램명: 실습 3 - Pandas EDA, Polars Lazy, DuckDB SQL 성능 비교
작성자: 임해안
작성일: 2026-07-21

목적:
    sales_100k.csv의 amount 이상치를 IQR 방식으로 제거하고, region·category별
    매출 집계를 Pandas, Polars Lazy API, DuckDB SQL로 각각 수행·비교한다.

입력 데이터:
    sales_100k.csv (필수 컬럼: region, category, amount)

변경 이력:
    - 2026-07-21: 실습 3의 EDA, IQR 이상치 처리, 세 도구 집계·성능 비교 구현
"""

from __future__ import annotations

import csv
import sys
import timeit
from pathlib import Path

try:
    import duckdb
    import pandas as pd
    import polars as pl
except ImportError as error:
    package_name = error.name or "필수 패키지"
    raise SystemExit(
        f"'{package_name}' 패키지가 필요합니다. "
        "'.venv/bin/python -m pip install -r requirements.txt'를 실행하세요."
    ) from error


DATA_FILE = Path("sales_100k.csv")
REQUIRED_COLUMNS = {"region", "category", "amount"}
TIMEIT_NUMBER = 5


def validate_input_file(data_file: Path) -> None:
    """CSV 파일 존재 여부와 필수 헤더를 분석 전에 검증한다."""
    if not data_file.is_file():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {data_file}")

    try:
        with data_file.open("r", encoding="utf-8-sig", newline="") as file:
            header = csv.reader(file)
            columns = next(header, None)
    except UnicodeDecodeError as error:
        raise ValueError("CSV 파일은 UTF-8 또는 UTF-8 BOM 인코딩이어야 합니다.") from error

    if not columns:
        raise ValueError("CSV 파일에 헤더 행이 없습니다.")

    missing_columns = REQUIRED_COLUMNS - set(columns)
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {sorted(missing_columns)}")


def load_and_explore_with_pandas(data_file: Path) -> tuple[pd.DataFrame, float, float]:
    """Pandas EDA를 출력하고 IQR 정상 범위 및 정제 DataFrame을 반환한다."""
    print("[실습 3-1] Pandas EDA 및 IQR 이상치 처리")
    df = pd.read_csv(data_file, encoding="utf-8-sig")

    if df.empty:
        raise ValueError("분석할 데이터 행이 없습니다.")

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    invalid_amount_count = df["amount"].isna().sum()
    if invalid_amount_count:
        print(f"amount 숫자 변환 불가/결측치: {invalid_amount_count}건")

    print("데이터 크기:", df.shape)
    print("\nDataFrame 정보:")
    df.info()
    print("\n기술 통계:")
    print(df.describe(include="all"))
    print("\n컬럼별 결측치 수:")
    print(df.isnull().sum())

    amount = df["amount"].dropna()
    if amount.empty:
        raise ValueError("amount 컬럼에 분석 가능한 숫자 값이 없습니다.")

    q1 = amount.quantile(0.25)
    q3 = amount.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    clean_df = df.loc[df["amount"].between(lower_bound, upper_bound)].copy()

    print(f"\nQ1={q1:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}")
    print(f"정상 범위: {lower_bound:.2f} ~ {upper_bound:.2f}")
    print(f"이상치 제거 전 행 수: {len(df)}")
    print(f"이상치 제거 후 행 수: {len(clean_df)}")
    print(f"제거된 이상치 수: {len(df) - len(clean_df)}")
    return clean_df, lower_bound, upper_bound


def pandas_aggregate(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Pandas named aggregation으로 지역·카테고리별 매출을 집계한다."""
    return (
        clean_df.dropna(subset=["region", "category", "amount"])
        .groupby(["region", "category"], as_index=False)
        .agg(
            total=("amount", "sum"),
            mean=("amount", "mean"),
            count=("amount", "count"),
        )
        .sort_values("total", ascending=False, kind="stable")
        .reset_index(drop=True)
    )


def polars_lazy_aggregate(data_file: Path, lower_bound: float, upper_bound: float) -> pl.DataFrame:
    """scan_csv부터 collect까지 Polars Lazy 체인으로 동일한 집계를 수행한다."""
    return (
        pl.scan_csv(data_file, schema_overrides={"amount": pl.Float64})
        .filter(
            pl.col("amount").is_not_null()
            & pl.col("region").is_not_null()
            & pl.col("category").is_not_null()
            & pl.col("amount").is_between(lower_bound, upper_bound)
        )
        .group_by(["region", "category"])
        .agg(
            pl.col("amount").sum().alias("total"),
            pl.col("amount").mean().alias("mean"),
            pl.col("amount").count().alias("count"),
        )
        .sort("total", descending=True)
        .collect()
    )


def duckdb_aggregate(data_file: Path, lower_bound: float, upper_bound: float) -> pd.DataFrame:
    """DuckDB SQL GROUP BY로 IQR 정제 데이터의 동일 집계를 수행한다."""
    query = """
        SELECT
            region,
            category,
            SUM(amount) AS total,
            AVG(amount) AS mean,
            COUNT(amount) AS count
        FROM read_csv_auto(?)
        WHERE amount IS NOT NULL
          AND region IS NOT NULL
          AND category IS NOT NULL
          AND amount BETWEEN ? AND ?
        GROUP BY region, category
        ORDER BY total DESC
    """
    with duckdb.connect() as connection:
        return connection.execute(query, [str(data_file), lower_bound, upper_bound]).df()


def assert_same_results(
    pandas_result: pd.DataFrame,
    polars_result: pl.DataFrame,
    duckdb_result: pd.DataFrame,
) -> None:
    """세 도구의 집계 결과가 동일한지 정렬·반올림 후 검증한다."""
    expected = pandas_result.sort_values(["region", "category"]).reset_index(drop=True)
    # to_pandas()는 별도의 pyarrow 설치를 요구할 수 있어 dict 변환을 사용한다.
    polars_as_pandas = (
        pd.DataFrame(polars_result.to_dicts())
        .sort_values(["region", "category"])
        .reset_index(drop=True)
    )
    duckdb_sorted = duckdb_result.sort_values(["region", "category"]).reset_index(drop=True)

    for result in (expected, polars_as_pandas, duckdb_sorted):
        result["total"] = result["total"].round(8)
        result["mean"] = result["mean"].round(8)
        result["count"] = result["count"].astype("int64")

    pd.testing.assert_frame_equal(expected, polars_as_pandas, check_dtype=False)
    pd.testing.assert_frame_equal(expected, duckdb_sorted, check_dtype=False)


def compare_performance(data_file: Path, lower_bound: float, upper_bound: float) -> None:
    """동일한 반복 횟수로 Pandas·Polars Lazy·DuckDB 실행 시간을 측정한다."""
    def run_pandas() -> pd.DataFrame:
        timed_df = pd.read_csv(data_file, encoding="utf-8-sig")
        timed_df["amount"] = pd.to_numeric(timed_df["amount"], errors="coerce")
        return pandas_aggregate(
            timed_df.loc[timed_df["amount"].between(lower_bound, upper_bound)].copy()
        )

    pandas_seconds = timeit.timeit(run_pandas, number=TIMEIT_NUMBER)
    polars_seconds = timeit.timeit(
        lambda: polars_lazy_aggregate(data_file, lower_bound, upper_bound),
        number=TIMEIT_NUMBER,
    )
    duckdb_seconds = timeit.timeit(
        lambda: duckdb_aggregate(data_file, lower_bound, upper_bound),
        number=TIMEIT_NUMBER,
    )

    print(f"\n[실습 3-4] 성능 비교 (각 {TIMEIT_NUMBER}회 실행)")
    print(f"Pandas:       {pandas_seconds:.4f}초")
    print(f"Polars Lazy:  {polars_seconds:.4f}초")
    print(f"DuckDB SQL:   {duckdb_seconds:.4f}초")


def main() -> int:
    """실습 3의 네 가지 실습 항목을 순서대로 실행한다."""
    try:
        validate_input_file(DATA_FILE)
        clean_df, lower_bound, upper_bound = load_and_explore_with_pandas(DATA_FILE)

        print("\n[실습 3-2] Pandas named aggregation 결과")
        pandas_result = pandas_aggregate(clean_df)
        print(pandas_result)

        print("\n[실습 3-3] Polars Lazy API 결과")
        polars_result = polars_lazy_aggregate(DATA_FILE, lower_bound, upper_bound)
        print(polars_result)

        print("\n[실습 3-4] DuckDB SQL 결과")
        duckdb_result = duckdb_aggregate(DATA_FILE, lower_bound, upper_bound)
        print(duckdb_result)

        assert_same_results(pandas_result, polars_result, duckdb_result)
        print("\n세 도구의 집계 결과가 동일함을 확인했습니다.")
        compare_performance(DATA_FILE, lower_bound, upper_bound)
    except (FileNotFoundError, PermissionError, OSError, ValueError, pd.errors.ParserError) as error:
        print(f"실습 실행 오류: {error}", file=sys.stderr)
        return 1
    except duckdb.Error as error:
        print(f"DuckDB SQL 실행 오류: {error}", file=sys.stderr)
        return 1
    except AssertionError as error:
        print(f"집계 결과 검증 실패: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
