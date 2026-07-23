"""원본 데이터 무결성 검증, 로딩 비교, 결측치·중복값 정제 기능."""

import hashlib
import json
import time
from pathlib import Path
from statistics import median

import pandas as pd
import polars as pl

from adult_income.config import (
    BENCHMARK_REPEATS,
    COLUMNS,
    EXPECTED_INCOME_VALUES,
    INCOME_LABELS,
    MISSING_COLUMNS,
    NUMERIC_FEATURES,
)
from adult_income.console import get_logger, log_section

logger = get_logger(__name__)


def load_data_manifest(manifest_path: Path) -> dict[str, object]:
    """데이터 출처와 무결성 기준이 기록된 manifest를 읽는다."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"데이터 manifest가 없습니다: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        message = f"manifest는 UTF-8 파일이어야 합니다: {manifest_path}"
        raise ValueError(message) from error
    except json.JSONDecodeError as error:
        message = f"manifest JSON 형식이 올바르지 않습니다: {manifest_path}"
        raise ValueError(message) from error

    if not isinstance(manifest, dict):
        raise ValueError("manifest의 최상위 값은 JSON 객체여야 합니다.")
    required_keys = {"size_bytes", "sha256", "expected_rows", "expected_columns"}
    missing_keys = required_keys - manifest.keys()
    if missing_keys:
        raise ValueError(f"manifest 필수 항목이 없습니다: {sorted(missing_keys)}")
    return manifest


def calculate_sha256(file_path: Path) -> str:
    """큰 파일도 메모리에 한 번에 올리지 않고 SHA-256을 계산한다."""
    if not file_path.is_file():
        raise FileNotFoundError(f"해시를 계산할 파일이 없습니다: {file_path}")
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_data_file(
    data_path: Path,
    manifest_path: Path,
) -> dict[str, object]:
    """데이터 파일의 크기와 SHA-256이 manifest와 같은지 확인한다."""
    if not data_path.is_file():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {data_path}")

    manifest = load_data_manifest(manifest_path)
    actual_size = data_path.stat().st_size
    actual_sha256 = calculate_sha256(data_path)

    if actual_size != manifest["size_bytes"]:
        raise ValueError(
            "데이터 파일 크기가 manifest와 다릅니다: "
            f"{actual_size} != {manifest['size_bytes']}"
        )
    if actual_sha256.lower() != str(manifest["sha256"]).lower():
        raise ValueError("데이터 파일 SHA-256이 manifest와 다릅니다.")

    return {**manifest, "validated": True}


def load_with_pandas(data_path: Path) -> pd.DataFrame:
    """Adult 데이터를 Pandas DataFrame으로 불러온다."""
    try:
        return pd.read_csv(
            data_path,
            header=None,
            names=COLUMNS,
            na_values=["?", " ?"],
            skipinitialspace=True,
            encoding="utf-8",
        )
    except (OSError, UnicodeError, pd.errors.ParserError) as error:
        raise RuntimeError(f"Pandas로 데이터를 읽지 못했습니다: {data_path}") from error


def load_with_polars(data_path: Path) -> pl.DataFrame:
    """Adult 데이터를 Polars DataFrame으로 불러온다."""
    try:
        dataframe = pl.read_csv(
            data_path,
            has_header=False,
            new_columns=COLUMNS,
            schema_overrides={column: pl.String for column in COLUMNS},
            encoding="utf8",
        )
    except (OSError, pl.exceptions.PolarsError) as error:
        raise RuntimeError(f"Polars로 데이터를 읽지 못했습니다: {data_path}") from error
    # 원본 파일 끝의 빈 줄이 데이터 행으로 해석되는 경우를 제거한다.
    dataframe = dataframe.filter(
        ~pl.all_horizontal([pl.col(column_name).is_null() for column_name in COLUMNS])
    )
    dataframe = dataframe.with_columns(
        [
            pl.col(column_name).str.strip_chars().replace("?", None)
            for column_name in COLUMNS
        ]
    )
    return dataframe.with_columns(
        [pl.col(column_name).cast(pl.Int64) for column_name in NUMERIC_FEATURES]
    )


def compare_pandas_and_polars(
    data_path: Path,
    repeats: int = BENCHMARK_REPEATS,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """동일한 로컬 파일로 Pandas와 Polars 로딩 결과를 비교한다."""
    if repeats < 1:
        raise ValueError("로딩 비교 반복 횟수는 1 이상이어야 합니다.")
    pandas_times: list[float] = []
    polars_times: list[float] = []
    pandas_raw = pd.DataFrame()
    polars_raw = pl.DataFrame()

    for _ in range(repeats):
        pandas_start = time.perf_counter()
        pandas_raw = load_with_pandas(data_path)
        pandas_times.append(time.perf_counter() - pandas_start)

        polars_start = time.perf_counter()
        polars_raw = load_with_polars(data_path)
        polars_times.append(time.perf_counter() - polars_start)

    if pandas_raw.shape != polars_raw.shape:
        raise ValueError("Pandas와 Polars의 데이터 크기가 다릅니다.")
    if pandas_raw.columns.tolist() != polars_raw.columns:
        raise ValueError("Pandas와 Polars의 열 이름이 다릅니다.")

    pandas_memory_mb = pandas_raw.memory_usage(deep=True).sum() / 1024**2
    polars_memory_mb = polars_raw.estimated_size("mb")
    pandas_missing = pandas_raw.isna().sum()
    polars_missing = pd.Series(
        polars_raw.null_count().row(0, named=True),
        name="Polars",
    )
    missing_comparison = pd.concat(
        [pandas_missing.rename("Pandas"), polars_missing],
        axis=1,
    )
    missing_comparison = missing_comparison[missing_comparison.max(axis=1) > 0]
    type_comparison = pd.DataFrame(
        {
            "Pandas": [str(data_type) for data_type in pandas_raw.dtypes],
            "Polars": [str(polars_raw.schema[column]) for column in COLUMNS],
        },
        index=COLUMNS,
    )

    results = {
        "pandas_shape": pandas_raw.shape,
        "polars_shape": polars_raw.shape,
        "pandas_time_seconds": median(pandas_times),
        "polars_time_seconds": median(polars_times),
        "pandas_memory_mb": pandas_memory_mb,
        "polars_memory_mb": polars_memory_mb,
        "missing_comparison": missing_comparison,
        "type_comparison": type_comparison,
    }

    log_section(logger, "Pandas와 Polars 로딩 결과 비교")
    logger.info("비교 파일: %s", data_path)
    logger.info("반복 횟수: %d회 (중앙값 사용)", repeats)
    logger.info("Pandas 크기: %s", pandas_raw.shape)
    logger.info("Polars 크기: %s", polars_raw.shape)
    logger.info("Pandas 로딩 시간: %.6f초", median(pandas_times))
    logger.info("Polars 로딩 시간: %.6f초", median(polars_times))
    logger.info("Pandas 메모리: %.2f MB", pandas_memory_mb)
    logger.info("Polars 메모리: %.2f MB", polars_memory_mb)
    logger.info("\n[결측치 비교]\n%s", missing_comparison)
    logger.info("\n[자료형 비교]\n%s", type_comparison)
    return pandas_raw, results


def create_missing_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    """열별 결측치 개수와 비율을 계산한다."""
    summary = pd.DataFrame(
        {
            "결측치 개수": dataframe.isna().sum(),
            "결측치 비율(%)": (dataframe.isna().mean() * 100).round(2),
        }
    )
    return summary[summary["결측치 개수"] > 0].sort_values(
        "결측치 개수",
        ascending=False,
    )


def validate_clean_data(dataframe: pd.DataFrame) -> None:
    """정제 결과가 이후 분석에 사용할 수 있는 상태인지 확인한다."""
    if set(dataframe.columns) != {*COLUMNS, "income_label"}:
        raise ValueError("정제된 데이터의 열 구성이 예상과 다릅니다.")
    if dataframe.isna().any().any():
        raise ValueError("정제 후에도 결측치가 남아 있습니다.")
    if dataframe.duplicated().any():
        raise ValueError("정제 후에도 중복 행이 남아 있습니다.")
    if set(dataframe["income_label"].unique()) != {0, 1}:
        raise ValueError("income_label은 0과 1로만 구성되어야 합니다.")


def clean_data(
    raw_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """문자열, 결측치, 중복값과 목표 레이블을 처리한다."""
    if raw_dataframe.empty:
        raise ValueError("정제할 데이터가 비어 있습니다.")
    missing_columns = set(COLUMNS) - set(raw_dataframe.columns)
    if missing_columns:
        raise ValueError(f"원본 데이터에 필수 열이 없습니다: {sorted(missing_columns)}")

    dataframe = raw_dataframe.copy()
    string_columns = dataframe.select_dtypes(include=["object", "string"]).columns
    dataframe[string_columns] = dataframe[string_columns].apply(
        lambda column: column.str.strip()
    )

    income_values = set(dataframe["income"].dropna().unique())
    unexpected_values = income_values - EXPECTED_INCOME_VALUES
    if unexpected_values:
        raise ValueError(f"예상하지 못한 income 값: {unexpected_values}")

    dataframe["income_label"] = dataframe["income"].map(INCOME_LABELS)
    missing_before = create_missing_summary(dataframe)
    dataframe[MISSING_COLUMNS] = dataframe[MISSING_COLUMNS].fillna("Unknown")

    duplicate_count = int(dataframe.duplicated().sum())
    rows_before = len(dataframe)
    dataframe = dataframe.drop_duplicates().reset_index(drop=True)
    rows_after = len(dataframe)
    missing_after = create_missing_summary(dataframe)
    validate_clean_data(dataframe)

    results = {
        "missing_before": missing_before,
        "missing_after": missing_after,
        "duplicate_count": duplicate_count,
        "rows_before": rows_before,
        "rows_after": rows_after,
    }

    log_section(logger, "결측치와 중복값 처리")
    logger.info("[처리 전 결측치]\n%s", missing_before)
    logger.info("\n[처리 후 결측치 개수]\n%d", dataframe.isna().sum().sum())
    logger.info("\n중복 행: %s개", f"{duplicate_count:,}")
    logger.info("처리 전 행 수: %s개", f"{rows_before:,}")
    logger.info("처리 후 행 수: %s개", f"{rows_after:,}")
    return dataframe, results
