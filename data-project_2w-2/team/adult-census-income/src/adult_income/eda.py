"""기본 탐색적 데이터 분석(EDA) 요약값을 계산하고 기록한다."""

from io import StringIO

import pandas as pd

from adult_income.config import CORRELATION_COLUMNS
from adult_income.console import get_logger, log_section

logger = get_logger(__name__)


def perform_eda(dataframe: pd.DataFrame) -> dict[str, object]:
    """데이터의 구조, 분포와 그룹별 요약값을 확인한다."""
    if dataframe.empty:
        raise ValueError("EDA를 수행할 데이터가 비어 있습니다.")
    required_columns = {*CORRELATION_COLUMNS, "income"}
    missing_columns = required_columns - set(dataframe.columns)
    if missing_columns:
        raise ValueError(f"EDA에 필요한 열이 없습니다: {sorted(missing_columns)}")

    numeric_columns = dataframe.select_dtypes(include="number").columns.tolist()
    categorical_columns = dataframe.select_dtypes(
        include=["object", "category", "string"]
    ).columns.tolist()

    numeric_summary = dataframe[numeric_columns].describe().round(2)
    categorical_summary = dataframe[categorical_columns].describe().T
    unique_summary = pd.DataFrame(
        {"고유값 개수": dataframe[categorical_columns].nunique()}
    ).sort_values("고유값 개수", ascending=False)
    income_distribution = pd.DataFrame(
        {
            "개수": dataframe["income"].value_counts(),
            "비율(%)": (dataframe["income"].value_counts(normalize=True) * 100).round(
                2
            ),
        }
    )
    group_mean = (
        dataframe.groupby("income")[
            [
                "age",
                "education-num",
                "hours-per-week",
                "capital-gain",
            ]
        ]
        .mean()
        .round(2)
    )
    correlation_matrix = dataframe[CORRELATION_COLUMNS].corr()

    results = {
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "unique_summary": unique_summary,
        "income_distribution": income_distribution,
        "group_mean": group_mean,
        "correlation_matrix": correlation_matrix,
    }

    # DataFrame.info()는 반환값이 없으므로 문자열 버퍼에 담아 로그로 남긴다.
    info_buffer = StringIO()
    dataframe.info(buf=info_buffer)

    log_section(logger, "기본 EDA")
    logger.info("[처음 5개 행]\n%s", dataframe.head())
    logger.info("\n데이터 크기: %s", dataframe.shape)
    logger.info("\n[데이터 정보]\n%s", info_buffer.getvalue().rstrip())
    logger.info("\n[수치형 변수 기술통계]\n%s", numeric_summary)
    logger.info("\n[범주형 변수 기술통계]\n%s", categorical_summary)
    logger.info("\n[범주형 변수별 고유값 개수]\n%s", unique_summary)
    logger.info("\n[소득 클래스 분포]\n%s", income_distribution)
    logger.info("\n[소득 그룹별 주요 수치형 변수 평균]\n%s", group_mean)
    return results
