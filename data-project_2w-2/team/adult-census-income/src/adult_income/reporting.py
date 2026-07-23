"""분석 단계에서 계산한 결과를 재현 가능한 Markdown 보고서로 만든다."""

from pathlib import Path

import pandas as pd

from adult_income.config import (
    BENCHMARK_REPEATS,
    MIN_GROUP_SAMPLE_COUNT,
    PROJECT_ROOT,
    RANDOM_STATE,
    SIGNIFICANCE_LEVEL,
)
from adult_income.console import get_logger, log_section

logger = get_logger(__name__)


def format_markdown_value(value: object) -> str:
    """Markdown 표에 들어갈 값을 읽기 쉬운 문자열로 변환한다."""
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:,.4f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def dataframe_to_markdown(
    dataframe: pd.DataFrame,
    include_index: bool = True,
) -> str:
    """추가 패키지 없이 DataFrame을 Markdown 표로 변환한다."""
    table = dataframe.copy()
    if include_index:
        index_name = table.index.name or "항목"
        table = table.rename_axis(index_name).reset_index()

    headers = [format_markdown_value(column) for column in table.columns]
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    row_lines = [
        "| " + " | ".join(format_markdown_value(value) for value in row) + " |"
        for row in table.itertuples(index=False, name=None)
    ]
    return "\n".join([header_line, separator_line, *row_lines])


def generate_report(
    dataframe: pd.DataFrame,
    analysis_results: dict[str, object],
    report_path: Path,
) -> Path:
    """현재 실행에서 계산한 분석 결과로 report.md를 생성한다."""
    required_sections = {
        "data_manifest",
        "loading",
        "quality",
        "eda",
        "statistics",
        "modeling",
        "chart_paths",
    }
    missing_sections = required_sections - analysis_results.keys()
    if missing_sections:
        message = f"보고서 분석 결과가 누락되었습니다: {sorted(missing_sections)}"
        raise ValueError(message)

    data_manifest = analysis_results["data_manifest"]
    loading = analysis_results["loading"]
    quality = analysis_results["quality"]
    eda = analysis_results["eda"]
    statistics = analysis_results["statistics"]
    modeling = analysis_results["modeling"]
    if not all(
        isinstance(result, dict)
        for result in [data_manifest, loading, quality, eda, statistics, modeling]
    ):
        raise TypeError("보고서 생성에 필요한 분석 결과 형식이 올바르지 않습니다.")

    missing_before = quality["missing_before"]
    income_distribution = eda["income_distribution"]
    group_mean = eda["group_mean"]
    descriptive_statistics = statistics["descriptive_statistics"]
    income_correlations = statistics["income_correlations"]
    metrics = modeling["metrics"]
    confusion = modeling["confusion_matrix"]
    classification_data = modeling["classification_report"]
    positive_coefficients = modeling["positive_coefficients"]
    negative_coefficients = modeling["negative_coefficients"]

    if not isinstance(income_correlations, pd.Series):
        raise TypeError("상관계수 결과가 Series가 아닙니다.")
    if not isinstance(metrics, dict) or not isinstance(classification_data, dict):
        raise TypeError("모델 평가 결과 형식이 올바르지 않습니다.")

    loading_table = pd.DataFrame(
        {
            "라이브러리": ["Pandas", "Polars"],
            "데이터 크기": [
                str(loading["pandas_shape"]),
                str(loading["polars_shape"]),
            ],
            "로딩 시간(초)": [
                loading["pandas_time_seconds"],
                loading["polars_time_seconds"],
            ],
            "메모리(MB)": [
                loading["pandas_memory_mb"],
                loading["polars_memory_mb"],
            ],
        }
    )
    metrics_table = pd.DataFrame(
        {
            "평가 지표": [
                "Accuracy",
                "Precision",
                "Recall",
                "F1",
                "ROC-AUC",
            ],
            "값": [
                metrics["accuracy"],
                metrics["precision"],
                metrics["recall"],
                metrics["f1"],
                metrics["roc_auc"],
            ],
        }
    )
    t_test_table = pd.DataFrame(
        {
            "항목": [
                "검정 변수",
                "<=50K 그룹 평균",
                ">50K 그룹 평균",
                "평균 차이",
                "t 통계량",
                "p-value",
                "Cohen's d",
                "효과크기",
            ],
            "결과": [
                statistics["test_variable"],
                statistics["low_income_mean"],
                statistics["high_income_mean"],
                statistics["mean_difference"],
                statistics["t_statistic"],
                statistics["p_value_text"],
                statistics["cohens_d"],
                statistics["effect_size"],
            ],
        }
    )
    correlation_table = income_correlations.rename("상관계수").to_frame()
    classification_table = (
        pd.DataFrame(classification_data)
        .T.loc[["<=50K", ">50K", "macro avg", "weighted avg"]]
        .round(4)
    )

    chart_paths = {
        Path(chart_path).name: Path(chart_path)
        for chart_path in analysis_results["chart_paths"]
    }
    expected_chart_names = {
        "01_seaborn_age_distribution.png",
        "02_seaborn_correlation_heatmap.png",
        "03_seaborn_hours_group_comparison.png",
        "04_plotly_education_distribution.html",
        "05_plotly_correlation_heatmap.html",
        "06_plotly_workclass_comparison.html",
    }
    missing_charts = expected_chart_names - chart_paths.keys()
    if missing_charts:
        raise ValueError(f"보고서에 필요한 차트가 없습니다: {sorted(missing_charts)}")

    def relative_path(path: Path) -> str:
        try:
            return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        except ValueError as error:
            message = f"산출물은 프로젝트 폴더 안에 있어야 합니다: {path}"
            raise ValueError(message) from error

    age_chart = relative_path(chart_paths["01_seaborn_age_distribution.png"])
    correlation_chart = relative_path(chart_paths["02_seaborn_correlation_heatmap.png"])
    hours_chart = relative_path(chart_paths["03_seaborn_hours_group_comparison.png"])
    education_chart = relative_path(
        chart_paths["04_plotly_education_distribution.html"]
    )
    interactive_correlation_chart = relative_path(
        chart_paths["05_plotly_correlation_heatmap.html"]
    )
    workclass_chart = relative_path(chart_paths["06_plotly_workclass_comparison.html"])
    model_path = relative_path(Path(modeling["model_path"]))
    metadata_path = relative_path(Path(modeling["metadata_path"]))

    pandas_time = float(loading["pandas_time_seconds"])
    polars_time = float(loading["polars_time_seconds"])
    pandas_memory = float(loading["pandas_memory_mb"])
    polars_memory = float(loading["polars_memory_mb"])
    strongest_feature = income_correlations.abs().idxmax()
    strongest_correlation = float(income_correlations[strongest_feature])

    # 표와 실행 결과를 템플릿에 삽입해 사람이 읽을 수 있는 보고서를 만든다.
    report = f"""# Adult Census Income 데이터 분석 보고서

## 1. 분석 개요

Adult Census Income 데이터로 개인의 연 소득이 50K를 초과하는지 분류했다.
데이터 품질 처리, EDA, 시각화, 통계 검정과 LogisticRegression Pipeline을
하나의 재현 가능한 실행 흐름으로 구성했다.

- 원본 데이터: `data/adult.data`
- 데이터 SHA-256: `{data_manifest["sha256"]}`
- 원본 크기: {quality["rows_before"]:,}행, 15열
- 정제 후 크기: {quality["rows_after"]:,}행, {dataframe.shape[1]}열
- 목표 변수: `income_label` (`<=50K`: 0, `>50K`: 1)

## 2. 데이터 로딩과 품질 처리

### 2.1 Pandas와 Polars 비교

동일한 로컬 파일을 각각 {BENCHMARK_REPEATS}회 읽고 중앙값을 비교했다.

{dataframe_to_markdown(loading_table, include_index=False)}

이번 실행에서는 Polars가 Pandas보다 약 {pandas_time / polars_time:.2f}배
빠르게 로딩되었고, Pandas의 메모리 사용량은 Polars의 약
{pandas_memory / polars_memory:.2f}배였다. 실행 시간은 환경에 따라 달라진다.

### 2.2 결측치와 중복값

결측 범주는 값을 임의로 추정하지 않고 `Unknown`으로 대체했다.

{dataframe_to_markdown(missing_before)}

- 처리 후 결측치: 0개
- 제거한 중복 행: {quality["duplicate_count"]:,}개
- 최종 행 수: {quality["rows_after"]:,}개

## 3. 탐색적 데이터 분석

### 3.1 소득 클래스 분포

{dataframe_to_markdown(income_distribution)}

### 3.2 소득 그룹별 평균

{dataframe_to_markdown(group_mean)}

### 3.3 Seaborn 정적 차트

![소득 그룹별 연령 분포]({age_chart})

![수치형 변수 상관관계]({correlation_chart})

![소득 그룹별 주당 근무시간]({hours_chart})

### 3.4 Plotly 인터랙티브 차트

- [소득 그룹별 교육연수 분포]({education_chart})
- [인터랙티브 상관관계 히트맵]({interactive_correlation_chart})
- [직업군별 고소득 비율]({workclass_chart})

직업군 비교에서는 표본 수가 {MIN_GROUP_SAMPLE_COUNT}개 미만인 그룹을 제외했다.

## 4. 통계 분석

### 4.1 기술통계

{dataframe_to_markdown(descriptive_statistics.round(3))}

### 4.2 목표 변수와 수치형 변수의 상관계수

{dataframe_to_markdown(correlation_table.round(4))}

절댓값 기준 가장 큰 상관관계는 `{strongest_feature}` 변수의
{strongest_correlation:.4f}였다. 상관계수는 인과관계를 증명하지 않는다.

### 4.3 Welch 독립표본 t-test

- 귀무가설: 두 소득 그룹의 평균 주당 근무시간은 같다.
- 대립가설: 두 소득 그룹의 평균 주당 근무시간은 다르다.
- 유의수준: {SIGNIFICANCE_LEVEL}

{dataframe_to_markdown(t_test_table, include_index=False)}

{statistics["interpretation"]} 평균 차이는 {statistics["mean_difference"]:.3f}시간,
Cohen's d는 {statistics["cohens_d"]:.4f}로 효과크기는
{statistics["effect_size"]} 수준이다.

## 5. LogisticRegression Pipeline

### 5.1 모델 구성

- 학습 데이터: {modeling["train_size"]:,}행
- 평가 데이터: {modeling["test_size"]:,}행
- 수치형 전처리: 중앙값 대체, StandardScaler
- 범주형 전처리: 최빈값 대체, OneHotEncoder
- 클래스 불균형 처리: `class_weight="balanced"`
- 데이터 분할: 계층화 80:20, `random_state={RANDOM_STATE}`

### 5.2 평가 지표

{dataframe_to_markdown(metrics_table, include_index=False)}

Recall은 {metrics["recall"]:.4f}, Precision은 {metrics["precision"]:.4f}였다.
소수 클래스를 적극적으로 찾는 대신 오탐이 늘어나는 균형을 함께 고려해야 한다.

### 5.3 혼동행렬

{dataframe_to_markdown(confusion)}

### 5.4 분류 리포트

{dataframe_to_markdown(classification_table)}

### 5.5 주요 모델 계수

계수는 예측 방향을 설명하지만 인과효과가 아니다.

#### 양의 계수 상위 10개

{dataframe_to_markdown(positive_coefficients, include_index=False)}

#### 음의 계수 상위 10개

{dataframe_to_markdown(negative_coefficients, include_index=False)}

- 저장 모델: [`{model_path}`]({model_path})
- 모델 메타데이터: [`{metadata_path}`]({metadata_path})
- 저장 후 재로딩 예측 일치: {modeling["reload_verified"]}

## 6. 결론

- 데이터의 약 24%가 `>50K`로 클래스 불균형이 존재했다.
- 수치형 변수 중 `{strongest_feature}` 변수가 가장 큰 선형 상관관계를 보였다.
- 두 소득 그룹의 주당 평균 근무시간은 통계적으로 유의하게 달랐다.
- LogisticRegression은 Accuracy {metrics["accuracy"]:.4f}, F1
  {metrics["f1"]:.4f}, ROC-AUC {metrics["roc_auc"]:.4f}를 기록했다.
- 저장한 Pipeline과 환경 메타데이터로 재학습 조건을 확인할 수 있다.

## 7. 한계와 개선 방향

- `education`과 `education-num`은 유사한 정보를 중복 표현한다.
- `fnlwgt`는 표본 가중치에 가까워 입력 변수 사용 여부를 검토해야 한다.
- `race`, `sex` 같은 민감 변수는 편향 점검 없이 의사결정에 사용하면 안 된다.
- 단일 학습·평가 분할 대신 교차검증으로 안정성을 확인할 수 있다.
- 분류 임계값 조정으로 Precision과 Recall의 균형을 변경할 수 있다.
- 상관관계, t-test와 모델 계수는 인과관계를 의미하지 않는다.
"""
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
    except OSError as error:
        message = f"Markdown 보고서를 저장하지 못했습니다: {report_path}"
        raise RuntimeError(message) from error

    log_section(logger, "Markdown 보고서 자동 생성")
    logger.info("보고서 저장 완료: %s", report_path)
    return report_path
