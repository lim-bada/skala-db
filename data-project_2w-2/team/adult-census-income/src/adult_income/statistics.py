"""기술통계, 상관관계, Welch t-test와 효과크기를 계산한다."""

import math

import pandas as pd
from scipy import stats

from adult_income.config import (
    NUMERIC_FEATURES,
    SIGNIFICANCE_LEVEL,
)
from adult_income.console import get_logger, log_section

logger = get_logger(__name__)


def describe_effect_size(cohens_d: float) -> str:
    """Cohen's d의 절댓값을 기준으로 효과크기를 설명한다."""
    absolute_effect = abs(cohens_d)
    if absolute_effect < 0.2:
        return "매우 작음"
    if absolute_effect < 0.5:
        return "작음"
    if absolute_effect < 0.8:
        return "중간"
    return "큼"


def perform_statistical_analysis(
    dataframe: pd.DataFrame,
    correlation_matrix: pd.DataFrame,
) -> dict[str, object]:
    """기술통계, 목표값 상관계수와 Welch t-test를 수행한다."""
    required_columns = {*NUMERIC_FEATURES, "income_label"}
    missing_columns = required_columns - set(dataframe.columns)
    if missing_columns:
        raise ValueError(f"통계 분석에 필요한 열이 없습니다: {sorted(missing_columns)}")
    if dataframe.empty:
        raise ValueError("통계 분석을 수행할 데이터가 비어 있습니다.")
    if "income_label" not in correlation_matrix.columns:
        raise ValueError("상관계수 행렬에 income_label이 없습니다.")

    descriptive_statistics = (
        dataframe[NUMERIC_FEATURES].describe().T[["mean", "std", "25%", "50%", "75%"]]
    )
    income_correlations = (
        correlation_matrix["income_label"]
        .drop("income_label")
        .sort_values(key=lambda values: values.abs(), ascending=False)
    )

    test_variable = "hours-per-week"
    low_income_group = dataframe.loc[
        dataframe["income_label"] == 0,
        test_variable,
    ]
    high_income_group = dataframe.loc[
        dataframe["income_label"] == 1,
        test_variable,
    ]
    if len(low_income_group) < 2 or len(high_income_group) < 2:
        raise ValueError("t-test에는 소득 그룹별로 최소 2개 표본이 필요합니다.")
    t_statistic, p_value = stats.ttest_ind(
        high_income_group,
        low_income_group,
        equal_var=False,
    )

    low_mean = float(low_income_group.mean())
    high_mean = float(high_income_group.mean())
    mean_difference = high_mean - low_mean
    pooled_variance = (
        (len(high_income_group) - 1) * high_income_group.var(ddof=1)
        + (len(low_income_group) - 1) * low_income_group.var(ddof=1)
    ) / (len(high_income_group) + len(low_income_group) - 2)
    if not math.isfinite(pooled_variance) or pooled_variance <= 0:
        raise ValueError("Cohen's d를 계산할 수 있는 분산이 없습니다.")
    cohens_d = float(mean_difference / pooled_variance**0.5)
    is_significant = bool(p_value < SIGNIFICANCE_LEVEL)
    p_value_text = "< 1e-300" if p_value == 0 else f"{p_value:.6g}"

    if is_significant:
        interpretation = (
            "귀무가설을 기각했다. 두 소득 그룹의 평균 주당 근무시간에는 "
            "통계적으로 유의한 차이가 있었다."
        )
    else:
        interpretation = (
            "귀무가설을 기각하지 못했다. 두 소득 그룹의 평균 주당 "
            "근무시간 차이가 통계적으로 유의하다고 보기 어려웠다."
        )

    results = {
        "descriptive_statistics": descriptive_statistics,
        "income_correlations": income_correlations,
        "test_variable": test_variable,
        "low_income_mean": low_mean,
        "high_income_mean": high_mean,
        "mean_difference": mean_difference,
        "t_statistic": float(t_statistic),
        "p_value": float(p_value),
        "p_value_text": p_value_text,
        "cohens_d": cohens_d,
        "effect_size": describe_effect_size(cohens_d),
        "is_significant": is_significant,
        "interpretation": interpretation,
    }

    log_section(logger, "기술통계·상관계수·t-test")
    logger.info(
        "[기술통계: 평균·표준편차·분위수]\n%s",
        descriptive_statistics.round(3),
    )
    logger.info(
        "\n[income_label과 수치형 변수의 상관계수]\n%s",
        income_correlations.round(4),
    )
    logger.info("\n[Welch 독립표본 t-test]")
    logger.info("귀무가설(H0): 두 소득 그룹의 평균 주당 근무시간은 같다.")
    logger.info("대립가설(H1): 두 소득 그룹의 평균 주당 근무시간은 다르다.")
    logger.info("유의수준: %s", SIGNIFICANCE_LEVEL)
    logger.info("<=50K 그룹 평균: %.3f시간", low_mean)
    logger.info(">50K 그룹 평균: %.3f시간", high_mean)
    logger.info("평균 차이(>50K - <=50K): %.3f시간", mean_difference)
    logger.info("t 통계량: %.4f", t_statistic)
    logger.info("p-value: %s", p_value_text)
    logger.info(interpretation)
    logger.info(
        "Cohen's d: %.4f (효과크기 %s)",
        cohens_d,
        describe_effect_size(cohens_d),
    )
    logger.warning("통계적으로 유의한 차이가 인과관계를 의미하지는 않는다.")
    return results
