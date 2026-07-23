"""데이터 무결성, 로딩 일치 여부, 정제 규칙을 검증한다."""

from pathlib import Path

import pandas as pd
import pytest

from adult_income.config import DATA_MANIFEST_PATH, DATA_PATH
from adult_income.data import (
    clean_data,
    compare_pandas_and_polars,
    load_data_manifest,
    load_with_pandas,
    load_with_polars,
    validate_data_file,
)


def test_invalid_manifest_has_clear_error(tmp_path: Path) -> None:
    manifest_path = tmp_path / "invalid.json"
    manifest_path.write_text("{잘못된 JSON", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON 형식"):
        load_data_manifest(manifest_path)


def test_loading_comparison_rejects_zero_repeats() -> None:
    with pytest.raises(ValueError, match="1 이상"):
        compare_pandas_and_polars(DATA_PATH, repeats=0)


def test_clean_data_rejects_empty_dataframe() -> None:
    with pytest.raises(ValueError, match="비어 있습니다"):
        clean_data(pd.DataFrame())


def test_data_file_matches_manifest() -> None:
    manifest = validate_data_file(DATA_PATH, DATA_MANIFEST_PATH)

    assert manifest["validated"] is True
    assert manifest["expected_rows"] == 32561


def test_pandas_and_polars_load_same_data_shape() -> None:
    pandas_dataframe = load_with_pandas(DATA_PATH)
    polars_dataframe = load_with_polars(DATA_PATH)

    assert pandas_dataframe.shape == (32561, 15)
    assert pandas_dataframe.shape == polars_dataframe.shape
    assert pandas_dataframe.columns.tolist() == polars_dataframe.columns


def test_clean_data_has_no_missing_or_duplicate_rows() -> None:
    raw_dataframe = load_with_pandas(DATA_PATH)
    cleaned_dataframe, quality_results = clean_data(raw_dataframe)

    assert cleaned_dataframe.isna().sum().sum() == 0
    assert cleaned_dataframe.duplicated().sum() == 0
    assert set(cleaned_dataframe["income_label"].unique()) == {0, 1}
    assert quality_results["duplicate_count"] == 24
