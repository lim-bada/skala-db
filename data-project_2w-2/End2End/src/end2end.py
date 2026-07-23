"""
프로그램명: Day 2 종합실습 - Adult Census Income 분석
작성자: 임해안
작성일: 2026-07-21

목적:
    Adult Census Income 데이터셋을 이용해 개인의 인구통계·교육·근무 특성과
    연 소득 50K 초과 여부의 관계를 탐색하고, 고소득 여부를 예측하는 분류
    Pipeline을 구축한다.

    Pandas와 Polars의 로딩 결과·성능을 비교하고 결측치·중복 처리와 EDA를
    수행한다. 이후 분포·상관관계·그룹 비교를 Seaborn과 Plotly로 각각
    시각화하고, 기술통계·상관계수·t-test를 통해 결과를 해석한다. 마지막으로
    전처리와 분류 모델을 하나의 sklearn Pipeline으로 구성해 평가·저장하고,
    전체 분석 결과를 report.md로 자동 생성한다.

핵심 분석 질문:
    1. 소득 그룹에 따라 나이 분포가 다른가?
    2. 어떤 수치형 변수가 고소득 여부와 높은 상관관계를 가지는가?
    3. 교육 수준에 따라 고소득자 비율이 다른가?

변경 이력:
    - 2026-07-21: Adult 데이터 다운로드 및 Pandas·Polars 로딩 비교 구현
    - 2026-07-21: 결측치·중복 처리, 정제 결과 검증 및 기본 EDA 구현
    - 2026-07-21: Seaborn·Plotly 소득 그룹별 나이 분포 시각화 구현
    - 2026-07-21: Seaborn·Plotly 수치형 변수 상관관계 히트맵 구현
    - 2026-07-21: Seaborn·Plotly 교육 수준별 고소득자 비율 비교 구현
    - 2026-07-21: 수치형 변수 평균·표준편차·분위수 기술통계 구현
    - 2026-07-21: 소득 이진 변수를 포함한 변수 간 상관계수 계산 구현
    - 2026-07-21: 소득 그룹별 주당 근무시간 독립표본 t-test와 해석 구현
    - 2026-07-21: 소득 분류 Pipeline 학습·평가 및 모델 저장·재로딩 구현
    - 2026-07-21: 전체 분석 결과 report.md 자동 생성 구현
    - 2026-07-21: 시각화별 목적·해석·도구 차이 보고서 설명 보강
    - 2026-07-21: 분석 목적·핵심 질문과 End-to-End 흐름 머리말 보강
"""

from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import joblib
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import polars as pl
    import plotly.express as px
    import seaborn as sns
    from scipy.stats import ttest_ind
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
except ImportError as error:
    package_name = error.name or "필수 패키지"
    raise SystemExit(
        f"'{package_name}' 패키지가 필요합니다. "
        "'python -m pip install -r requirements.txt'를 실행하세요."
    ) from error


DATA_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
PROJECT_DIRECTORY = Path(__file__).resolve().parents[1]
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
DATA_FILE = DATA_DIRECTORY / "adult.csv"
OUTPUT_DIRECTORY = PROJECT_DIRECTORY / "outputs"
SEABORN_DISTRIBUTION_FILE = OUTPUT_DIRECTORY / "age_distribution_seaborn.png"
PLOTLY_DISTRIBUTION_FILE = OUTPUT_DIRECTORY / "age_distribution_plotly.html"
SEABORN_CORRELATION_FILE = OUTPUT_DIRECTORY / "correlation_seaborn.png"
PLOTLY_CORRELATION_FILE = OUTPUT_DIRECTORY / "correlation_plotly.html"
SEABORN_GROUP_FILE = OUTPUT_DIRECTORY / "education_income_seaborn.png"
PLOTLY_GROUP_FILE = OUTPUT_DIRECTORY / "education_income_plotly.html"
MODEL_FILE = OUTPUT_DIRECTORY / "income_classification_pipeline.joblib"
REPORT_FILE = PROJECT_DIRECTORY / "report.md"
COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education-num",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
    "native-country",
    "income",
]
MISSING_CATEGORICAL_COLUMNS = ["workclass", "occupation", "native-country"]
EDA_NUMERIC_COLUMNS = [
    "age",
    "education-num",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
]
STATISTICS_NUMERIC_COLUMNS = ["age", "fnlwgt", *EDA_NUMERIC_COLUMNS[1:]]
EDA_CATEGORICAL_COLUMNS = ["income", "sex", "education", "occupation"]
MODEL_NUMERIC_FEATURES = STATISTICS_NUMERIC_COLUMNS
MODEL_CATEGORICAL_FEATURES = [
    "workclass",
    "education",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "native-country",
]
MODEL_FEATURES = MODEL_NUMERIC_FEATURES + MODEL_CATEGORICAL_FEATURES
SIGNIFICANCE_LEVEL = 0.05
RANDOM_STATE = 42
TEST_SIZE = 0.2


def download_dataset(data_url: str, data_file: Path) -> None:
    """Adult 원본 데이터가 없으면 UCI 저장소에서 내려받아 로컬에 저장한다."""
    if data_file.is_file() and data_file.stat().st_size > 0:
        print(f"기존 데이터 파일 사용: {data_file}")
        return

    data_file.parent.mkdir(parents=True, exist_ok=True)
    request = Request(data_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        data_file.write_bytes(response.read())

    if data_file.stat().st_size == 0:
        raise ValueError("다운로드한 데이터 파일이 비어 있습니다.")
    print(f"데이터 다운로드 완료: {data_file}")


def load_with_pandas(data_file: Path) -> tuple[pd.DataFrame, float]:
    """Adult CSV를 Pandas DataFrame으로 읽고 소요 시간을 반환한다."""
    start_time = perf_counter()
    dataframe = pd.read_csv(
        data_file,
        header=None,
        names=COLUMNS,
        na_values="?",
        skipinitialspace=True,
    )
    elapsed_time = perf_counter() - start_time
    return dataframe, elapsed_time


def load_with_polars(data_file: Path) -> tuple[pl.DataFrame, float]:
    """동일한 Adult CSV를 Polars DataFrame으로 읽고 문자열 공백을 정리한다."""
    start_time = perf_counter()
    dataframe = pl.read_csv(
        data_file,
        has_header=False,
        new_columns=COLUMNS,
        null_values=" ?",
    ).filter(pl.col("age").is_not_null()).with_columns(
        pl.col(pl.String).str.strip_chars()
    )
    elapsed_time = perf_counter() - start_time
    return dataframe, elapsed_time


def compare_loading_results(
    pandas_df: pd.DataFrame,
    pandas_seconds: float,
    polars_df: pl.DataFrame,
    polars_seconds: float,
) -> None:
    """두 도구의 데이터 크기·결측치·로딩 시간을 출력하고 결과를 검증한다."""
    pandas_shape = pandas_df.shape
    polars_shape = polars_df.shape
    if pandas_shape != polars_shape:
        raise AssertionError(
            f"Pandas와 Polars의 데이터 크기가 다릅니다: {pandas_shape} != {polars_shape}"
        )

    pandas_missing = int(pandas_df.isna().sum().sum())
    polars_missing = int(polars_df.null_count().sum_horizontal().item())

    print("\n[데이터 로딩 비교]")
    print(f"Pandas 크기: {pandas_shape}, 로딩 시간: {pandas_seconds:.6f}초")
    print(f"Polars 크기: {polars_shape}, 로딩 시간: {polars_seconds:.6f}초")
    print(f"Pandas 전체 결측치: {pandas_missing:,}개")
    print(f"Polars 전체 결측치: {polars_missing:,}개")

    if pandas_missing != polars_missing:
        raise AssertionError(
            "Pandas와 Polars에서 인식한 결측치 수가 서로 다릅니다: "
            f"{pandas_missing} != {polars_missing}"
        )


def print_data_quality(pandas_df: pd.DataFrame, polars_df: pl.DataFrame) -> None:
    """정제 전 데이터 샘플, 컬럼별 결측치와 전체 중복 행 수를 확인한다."""
    pandas_missing = pandas_df.isna().sum()
    missing_summary = pd.DataFrame(
        {
            "missing_count": pandas_missing,
            "missing_ratio_percent": pandas_missing / len(pandas_df) * 100,
        }
    )
    missing_summary = missing_summary.loc[missing_summary["missing_count"] > 0]

    pandas_duplicates = len(pandas_df) - len(pandas_df.drop_duplicates())
    polars_duplicates = polars_df.height - polars_df.unique().height
    if pandas_duplicates != polars_duplicates:
        raise AssertionError(
            "Pandas와 Polars의 중복 행 수가 서로 다릅니다: "
            f"{pandas_duplicates} != {polars_duplicates}"
        )

    print("\n[정제 전 데이터 샘플 - 상위 5개 행]")
    print(pandas_df.head())
    print("\n[정제 전 데이터 품질]")
    print("컬럼별 결측치 수·비율:")
    print(missing_summary.round(2))
    print(f"중복 행: {pandas_duplicates:,}건")


def clean_with_pandas(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Pandas에서 중복 행을 제거하고 범주형 결측치를 Unknown으로 대체한다."""
    clean_df = dataframe.drop_duplicates().copy()
    clean_df[MISSING_CATEGORICAL_COLUMNS] = clean_df[
        MISSING_CATEGORICAL_COLUMNS
    ].fillna("Unknown")
    return clean_df


def clean_with_polars(dataframe: pl.DataFrame) -> pl.DataFrame:
    """Polars에서 중복 행을 제거하고 범주형 결측치를 Unknown으로 대체한다."""
    return dataframe.unique(maintain_order=True).with_columns(
        pl.col(MISSING_CATEGORICAL_COLUMNS).fill_null("Unknown")
    )


def validate_cleaning_results(
    raw_pandas_df: pd.DataFrame,
    clean_pandas_df: pd.DataFrame,
    clean_polars_df: pl.DataFrame,
) -> None:
    """정제 후 두 DataFrame의 크기·결측치·중복 제거 결과가 같은지 검증한다."""
    if clean_pandas_df.shape != clean_polars_df.shape:
        raise AssertionError(
            "정제 후 Pandas와 Polars의 데이터 크기가 다릅니다: "
            f"{clean_pandas_df.shape} != {clean_polars_df.shape}"
        )

    pandas_missing = int(clean_pandas_df.isna().sum().sum())
    polars_missing = int(clean_polars_df.null_count().sum_horizontal().item())
    pandas_duplicates = int(clean_pandas_df.duplicated().sum())
    polars_duplicates = int(clean_polars_df.is_duplicated().sum())
    if pandas_missing != 0 or polars_missing != 0:
        raise AssertionError(
            f"정제 후 결측치가 남았습니다: Pandas={pandas_missing}, Polars={polars_missing}"
        )
    if pandas_duplicates != 0 or polars_duplicates != 0:
        raise AssertionError(
            "정제 후 중복 행이 남았습니다: "
            f"Pandas={pandas_duplicates}, Polars={polars_duplicates}"
        )

    print("\n[정제 결과]")
    print(f"정제 전 행 수: {len(raw_pandas_df):,}")
    print(f"정제 후 행 수: {len(clean_pandas_df):,}")
    print(f"제거한 중복 행 수: {len(raw_pandas_df) - len(clean_pandas_df):,}")
    print("정제 후 결측치: 0개")
    print("Pandas·Polars 정제 결과 검증 완료")


def run_basic_eda(dataframe: pd.DataFrame) -> None:
    """정제된 Adult 데이터의 구조와 주요 범주형 빈도를 출력한다."""
    print("\n[기본 EDA]")
    print(f"데이터 크기: {dataframe.shape}")
    print("\n상위 5개 행:")
    print(dataframe.head())
    print("\n컬럼 타입:")
    print(dataframe.dtypes)
    for column in EDA_CATEGORICAL_COLUMNS:
        print(f"\n{column} 빈도:")
        print(dataframe[column].value_counts(dropna=False))

    income_ratio = dataframe["income"].value_counts(normalize=True).mul(100).round(2)
    print("\nincome 클래스 비율(%):")
    print(income_ratio)


# 통계 분석 1: 주요 수치형 변수의 중심·산포·분포 위치 파악
def calculate_descriptive_statistics(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Adult 수치형 변수의 전반적인 크기·변동성과 분포 위치를 요약한다."""
    statistics = dataframe[STATISTICS_NUMERIC_COLUMNS].describe().T[
        ["mean", "std", "25%", "50%", "75%"]
    ]
    print("\n[통계 분석 1 - 주요 수치형 변수의 기술통계]")
    print("목적: 평균·표준편차·분위수로 변수별 중심, 변동성, 분포 위치를 파악합니다.")
    print(statistics.round(2))
    return statistics


def create_age_distribution_charts(dataframe: pd.DataFrame) -> None:
    """소득 그룹별 나이 분포를 Seaborn PNG와 Plotly HTML로 각각 저장한다."""
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(10, 6))
    sns.histplot(
        data=dataframe,
        x="age",
        hue="income",
        bins=30,
        kde=True,
        stat="density",
        common_norm=False,
        element="step",
        ax=axis,
    )
    axis.set_title("Age Distribution by Income Group")
    axis.set_xlabel("Age")
    axis.set_ylabel("Density")
    figure.tight_layout()
    figure.savefig(SEABORN_DISTRIBUTION_FILE, dpi=150, bbox_inches="tight")
    plt.close(figure)

    interactive_figure = px.histogram(
        dataframe,
        x="age",
        color="income",
        nbins=30,
        barmode="overlay",
        histnorm="probability density",
        marginal="box",
        opacity=0.65,
        title="Age Distribution by Income Group",
        labels={"age": "Age", "income": "Income", "count": "Density"},
    )
    interactive_figure.update_layout(
        xaxis_title="Age",
        yaxis_title="Density",
        legend_title="Income",
    )
    interactive_figure.write_html(
        PLOTLY_DISTRIBUTION_FILE,
        include_plotlyjs=True,
        full_html=True,
    )

    print("\n[분포 시각화]")
    print(f"Seaborn 정적 차트 저장: {SEABORN_DISTRIBUTION_FILE}")
    print(f"Plotly 인터랙티브 차트 저장: {PLOTLY_DISTRIBUTION_FILE}")


# 통계 분석 2: 수치형 특성과 고소득 여부의 선형 관계 탐색
def calculate_correlation_matrix(dataframe: pd.DataFrame) -> pd.DataFrame:
    """수치형 특성 중 고소득 여부와 선형 관계가 큰 변수를 탐색한다."""
    correlation_data = dataframe[EDA_NUMERIC_COLUMNS].copy()
    correlation_data["income_binary"] = dataframe["income"].eq(">50K").astype(int)
    correlation = correlation_data.corr()

    print("\n[통계 분석 2 - 수치형 특성과 고소득 여부의 Pearson 상관계수]")
    print("목적: 변수 간 선형 관계의 방향과 강도를 비교해 주요 관련 특성을 찾습니다.")
    print(correlation.round(3))
    return correlation


def create_correlation_charts(correlation: pd.DataFrame) -> None:
    """계산된 상관행렬을 Seaborn PNG와 Plotly HTML로 각각 저장한다."""
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        ax=axis,
    )
    axis.set_title("Correlation of Numeric Variables")
    figure.tight_layout()
    figure.savefig(SEABORN_CORRELATION_FILE, dpi=150, bbox_inches="tight")
    plt.close(figure)

    interactive_figure = px.imshow(
        correlation,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlation of Numeric Variables",
        labels={"x": "Variable", "y": "Variable", "color": "Correlation"},
    )
    interactive_figure.update_layout(
        xaxis_title="Variable",
        yaxis_title="Variable",
    )
    interactive_figure.write_html(
        PLOTLY_CORRELATION_FILE,
        include_plotlyjs=True,
        full_html=True,
    )

    print(f"Seaborn 정적 차트 저장: {SEABORN_CORRELATION_FILE}")
    print(f"Plotly 인터랙티브 차트 저장: {PLOTLY_CORRELATION_FILE}")


def create_education_income_charts(dataframe: pd.DataFrame) -> pd.DataFrame:
    """교육 수준별 고소득자 비율을 Seaborn PNG와 Plotly HTML로 저장한다."""
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    group_data = dataframe.assign(
        income_binary=dataframe["income"].eq(">50K").astype(int)
    )
    education_summary = (
        group_data.groupby(["education", "education-num"], as_index=False)
        .agg(
            total_count=("income", "size"),
            high_income_count=("income_binary", "sum"),
            high_income_rate=("income_binary", "mean"),
        )
        .sort_values("education-num")
    )
    education_summary["high_income_rate"] *= 100
    education_order = education_summary["education"].tolist()

    print("\n[교육 수준별 고소득자 그룹 비교]")
    print(
        education_summary[
            ["education", "total_count", "high_income_count", "high_income_rate"]
        ].to_string(index=False, float_format=lambda value: f"{value:.2f}")
    )

    figure, axis = plt.subplots(figsize=(14, 7))
    sns.barplot(
        data=education_summary,
        x="education",
        y="high_income_rate",
        order=education_order,
        color="steelblue",
        ax=axis,
    )
    axis.set_title("High-Income Rate by Education Level")
    axis.set_xlabel("Education Level")
    axis.set_ylabel("High-Income Rate (%)")
    axis.tick_params(axis="x", rotation=45)
    figure.tight_layout()
    figure.savefig(SEABORN_GROUP_FILE, dpi=150, bbox_inches="tight")
    plt.close(figure)

    interactive_figure = px.bar(
        education_summary,
        x="education",
        y="high_income_rate",
        text_auto=".1f",
        title="High-Income Rate by Education Level",
        labels={
            "education": "Education Level",
            "high_income_rate": "High-Income Rate (%)",
        },
        hover_data={
            "total_count": ":,",
            "high_income_count": ":,",
            "education-num": False,
        },
        category_orders={"education": education_order},
    )
    interactive_figure.update_layout(
        xaxis_title="Education Level",
        yaxis_title="High-Income Rate (%)",
    )
    interactive_figure.write_html(
        PLOTLY_GROUP_FILE,
        include_plotlyjs=True,
        full_html=True,
    )

    print(f"Seaborn 정적 차트 저장: {SEABORN_GROUP_FILE}")
    print(f"Plotly 인터랙티브 차트 저장: {PLOTLY_GROUP_FILE}")
    return education_summary


def run_hours_per_week_t_test(dataframe: pd.DataFrame) -> dict[str, float]:
    """두 소득 그룹의 평균 주당 근무시간 차이를 Welch t-test로 검정한다."""
    low_income_hours = dataframe.loc[
        dataframe["income"] == "<=50K", "hours-per-week"
    ].dropna()
    high_income_hours = dataframe.loc[
        dataframe["income"] == ">50K", "hours-per-week"
    ].dropna()
    if len(low_income_hours) < 2 or len(high_income_hours) < 2:
        raise ValueError("t-test에는 각 소득 그룹의 유효 데이터가 2건 이상 필요합니다.")

    t_statistic, p_value = ttest_ind(
        low_income_hours,
        high_income_hours,
        equal_var=False,
        nan_policy="omit",
    )

    print("\n[통계 분석 3 - 소득 그룹별 주당 근무시간 t-test]")
    print(
        f"<=50K: {len(low_income_hours):,}건, "
        f"평균={low_income_hours.mean():.2f}, 표준편차={low_income_hours.std():.2f}"
    )
    print(
        f">50K: {len(high_income_hours):,}건, "
        f"평균={high_income_hours.mean():.2f}, 표준편차={high_income_hours.std():.2f}"
    )
    print(f"t-statistic: {t_statistic:.6f}")
    p_value_text = "< 1e-300" if p_value == 0 else f"{p_value:.6g}"
    print(f"p-value: {p_value_text}")
    if p_value < SIGNIFICANCE_LEVEL:
        print(
            "해석: p < 0.05이므로 두 소득 그룹의 평균 주당 근무시간 차이는 "
            "통계적으로 유의미합니다."
        )
    else:
        print(
            "해석: p >= 0.05이므로 두 소득 그룹의 평균 주당 근무시간 차이가 "
            "유의미하다고 볼 근거가 부족합니다."
        )
    return {
        "low_income_count": float(len(low_income_hours)),
        "high_income_count": float(len(high_income_hours)),
        "low_income_mean": float(low_income_hours.mean()),
        "high_income_mean": float(high_income_hours.mean()),
        "t_statistic": float(t_statistic),
        "p_value": float(p_value),
    }


# ML Pipeline: 전처리와 소득 분류 모델 구성·학습·평가·저장
def build_income_pipeline() -> Pipeline:
    """수치형·범주형 전처리와 로지스틱 회귀를 하나의 Pipeline으로 구성한다."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, MODEL_NUMERIC_FEATURES),
            ("categorical", categorical_transformer, MODEL_CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


def train_evaluate_and_save_pipeline(dataframe: pd.DataFrame) -> dict[str, float]:
    """소득 분류 Pipeline을 학습·평가하고 joblib 저장 후 재로딩을 검증한다."""
    missing_features = set(MODEL_FEATURES) - set(dataframe.columns)
    if missing_features:
        raise ValueError(f"모델 학습에 필요한 컬럼이 없습니다: {sorted(missing_features)}")

    target = dataframe["income"].map({"<=50K": 0, ">50K": 1})
    if target.isna().any():
        raise ValueError("income 컬럼에 정의되지 않은 클래스가 포함되어 있습니다.")

    features = dataframe[MODEL_FEATURES]
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=target,
    )

    pipeline = build_income_pipeline()
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    pipeline_score = pipeline.score(x_test, y_test)
    accuracy = accuracy_score(y_test, predictions)
    f1 = f1_score(y_test, predictions)
    matrix = confusion_matrix(y_test, predictions)

    print("\n[ML Pipeline - 소득 분류 모델]")
    print(f"학습 데이터: {len(x_train):,}건")
    print(f"평가 데이터: {len(x_test):,}건")
    print(f"Pipeline score: {pipeline_score:.4f}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1 score: {f1:.4f}")
    print("Confusion matrix:")
    print(matrix)

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_FILE)
    reloaded_pipeline = joblib.load(MODEL_FILE)
    reloaded_predictions = reloaded_pipeline.predict(x_test)
    if not (predictions == reloaded_predictions).all():
        raise AssertionError("저장 전후 Pipeline의 예측 결과가 일치하지 않습니다.")

    print(f"모델 저장 및 재로딩 검증 완료: {MODEL_FILE}")
    return {"accuracy": accuracy, "f1": f1}


# 자동화: 분석 결과와 산출물 링크를 Markdown 보고서로 생성
def generate_report(
    raw_dataframe: pd.DataFrame,
    clean_dataframe: pd.DataFrame,
    pandas_seconds: float,
    polars_seconds: float,
    descriptive_statistics: pd.DataFrame,
    correlation: pd.DataFrame,
    education_summary: pd.DataFrame,
    t_test_results: dict[str, float],
    model_metrics: dict[str, float],
) -> None:
    """데이터 준비부터 모델 평가까지의 핵심 결과를 report.md로 자동 저장한다."""
    raw_missing = int(raw_dataframe.isna().sum().sum())
    duplicate_count = len(raw_dataframe) - len(raw_dataframe.drop_duplicates())
    high_income_education = education_summary.loc[
        education_summary["high_income_rate"].idxmax()
    ]
    low_income_age_mean = clean_dataframe.loc[
        clean_dataframe["income"] == "<=50K", "age"
    ].mean()
    high_income_age_mean = clean_dataframe.loc[
        clean_dataframe["income"] == ">50K", "age"
    ].mean()
    income_correlations = correlation["income_binary"].drop("income_binary")
    strongest_correlation_name = income_correlations.abs().idxmax()
    strongest_correlation_value = income_correlations[strongest_correlation_name]
    p_value = t_test_results["p_value"]
    p_value_text = "< 1e-300" if p_value == 0 else f"{p_value:.6g}"
    test_interpretation = (
        "두 소득 그룹의 평균 주당 근무시간 차이는 통계적으로 유의미하다."
        if p_value < SIGNIFICANCE_LEVEL
        else "두 소득 그룹의 평균 주당 근무시간 차이가 유의미하다고 볼 근거가 부족하다."
    )
    faster_tool = "Pandas" if pandas_seconds < polars_seconds else "Polars"
    speed_ratio = max(pandas_seconds, polars_seconds) / min(
        pandas_seconds, polars_seconds
    )

    report = f"""# Adult Census Income End-to-End 분석 보고서

## 1. 분석 목적

개인의 인구통계·교육·근무 특성과 연 소득 50K 초과 여부의 관계를 탐색하고,
전처리와 분류 모델을 결합한 Pipeline으로 고소득 여부를 예측한다.

핵심 질문은 다음과 같다.

1. 소득 그룹에 따라 나이 분포가 다른가?
2. 어떤 수치형 변수가 고소득 여부와 높은 상관관계를 가지는가?
3. 교육 수준에 따라 고소득자 비율이 다른가?

## 2. 데이터 준비

- 원본 데이터: {len(raw_dataframe):,}행 × {raw_dataframe.shape[1]}열
- 원본 결측치: {raw_missing:,}개
- 중복 제거: {duplicate_count:,}행
- 정제 데이터: {len(clean_dataframe):,}행 × {clean_dataframe.shape[1]}열
- Pandas 로딩 시간: {pandas_seconds:.6f}초
- Polars 로딩 시간: {polars_seconds:.6f}초
- 이번 실행에서는 {faster_tool}가 약 {speed_ratio:.2f}배 빠르게 로딩했다.

결측 범주형 값은 `Unknown`으로 대체하고 중복 행은 제거했다.

## 3. 시각화

### 3.1 소득 그룹별 나이 분포

![Seaborn 나이 분포](outputs/{SEABORN_DISTRIBUTION_FILE.name})

[Plotly 인터랙티브 나이 분포](outputs/{PLOTLY_DISTRIBUTION_FILE.name})

이 그래프는 두 소득 그룹에서 나이가 어떻게 분포하는지 비교한다. Seaborn 차트의
히스토그램은 구간별 밀도를, KDE 곡선은 전체적인 분포 형태를 보여준다. Plotly
차트에서는 막대에 마우스를 올려 구간별 값을 확인할 수 있고, 상단 박스플롯으로
중앙값과 사분위 범위를 함께 탐색할 수 있다.

`<=50K` 그룹의 평균 나이는 {low_income_age_mean:.2f}세이고 `>50K` 그룹은
{high_income_age_mean:.2f}세다. 고소득 그룹이 상대적으로 높은 연령대에 집중되어
있지만, 두 분포가 겹치므로 나이만으로 소득 그룹을 구분할 수는 없다.

### 3.2 수치형 변수 상관관계

![Seaborn 상관관계](outputs/{SEABORN_CORRELATION_FILE.name})

[Plotly 인터랙티브 상관관계](outputs/{PLOTLY_CORRELATION_FILE.name})

히트맵은 두 변수의 선형 관계를 -1부터 1 사이의 Pearson 상관계수로 표현한다.
0에 가까울수록 선형 관계가 약하며, 절댓값이 커질수록 관계가 강하다. Seaborn은
전체 행렬을 한눈에 비교하기 좋고, Plotly는 각 셀의 정확한 값을 hover로 확인하기
좋다.

고소득 여부와 절대 상관계수가 가장 큰 변수는 `{strongest_correlation_name}`이며
계수는 {strongest_correlation_value:.3f}이다. 모든 계수가 강한 수준은 아니므로
단일 변수보다 여러 특성을 함께 사용하는 모델이 적절하다. 또한 상관관계는
인과관계를 의미하지 않는다.

### 3.3 교육 수준별 고소득자 비율

![Seaborn 그룹 비교](outputs/{SEABORN_GROUP_FILE.name})

[Plotly 인터랙티브 그룹 비교](outputs/{PLOTLY_GROUP_FILE.name})

막대 높이는 교육 그룹의 전체 인원이 아니라 각 그룹 내 `>50K` 비율을 뜻한다.
교육 수준은 `education-num` 순서로 정렬했다. Seaborn 차트는 그룹 간 비율 변화를
빠르게 비교하기 좋고, Plotly 차트는 hover를 통해 전체 인원과 고소득자 수를 함께
확인할 수 있다.

가장 높은 고소득자 비율은 `{high_income_education['education']}`의
{high_income_education['high_income_rate']:.2f}%이며, 표본은
{int(high_income_education['total_count']):,}명이다. 전반적으로 교육 수준이
높을수록 고소득자 비율이 증가하지만, 그룹별 표본 수 차이와 다른 영향 변수를
고려해야 하며 교육 수준만으로 인과적인 결론을 내려서는 안 된다.

## 4. 통계 분석

### 4.1 주요 수치형 변수의 기술통계

나이, 표본 가중치, 교육 연수, 자본손익, 주당 근무시간의 평균으로 중심적인
수준을 확인하고, 표준편차로 값의 변동성을 비교한다. 25%·50%·75% 분위수는
극단값의 영향을 덜 받으면서 각 변수의 분포 위치와 비대칭성을 파악하기 위해
사용한다.

```text
{descriptive_statistics.round(2).to_string()}
```

### 4.2 수치형 특성과 고소득 여부의 Pearson 상관계수

각 수치형 특성과 `income_binary` 사이의 선형 관계 방향과 강도를 비교해 고소득
여부와 상대적으로 관련성이 큰 변수를 탐색한다. 상관계수는 -1에서 1 사이이며,
절댓값이 클수록 선형 관계가 강하지만 인과관계를 의미하지는 않는다.

```text
{correlation.round(3).to_string()}
```

고소득 여부와 절대 상관계수가 가장 큰 변수는 `{strongest_correlation_name}`이며,
상관계수는 {strongest_correlation_value:.3f}이다.

### 4.3 Welch 독립표본 t-test

- `<=50K` 평균 주당 근무시간: {t_test_results['low_income_mean']:.2f}시간
- `>50K` 평균 주당 근무시간: {t_test_results['high_income_mean']:.2f}시간
- t통계량: {t_test_results['t_statistic']:.6f}
- p-value: {p_value_text}
- 해석: {test_interpretation}

## 5. ML Pipeline

- 수치형 전처리: 중앙값 대체 + 표준화
- 범주형 전처리: 최빈값 대체 + 원핫 인코딩
- 모델: 클래스 가중치를 적용한 Logistic Regression
- Accuracy: {model_metrics['accuracy']:.4f}
- F1 score: {model_metrics['f1']:.4f}
- [저장 모델](outputs/{MODEL_FILE.name})

## 6. 결론 및 한계

교육 연수, 나이, 주당 근무시간은 고소득 여부와 양의 관계를 보였다. 특히 교육
수준이 높을수록 고소득자 비율이 증가하는 경향이 나타났다. 다만 상관관계와
t-test 결과는 인과관계를 의미하지 않는다. 또한 이 데이터에는 성별·인종과 같은
민감한 특성이 포함되어 있으므로 모델 결과를 실제 의사결정에 사용할 때 편향을
추가로 검토해야 한다.

이 보고서는 `src/end2end.py` 실행 결과로 자동 생성되었다.
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"\n자동 보고서 저장 완료: {REPORT_FILE}")


def main() -> int:
    """데이터 준비부터 분석·모델링·Markdown 보고서 생성까지 수행한다."""
    try:
        download_dataset(DATA_URL, DATA_FILE)
        pandas_df, pandas_seconds = load_with_pandas(DATA_FILE)
        polars_df, polars_seconds = load_with_polars(DATA_FILE)
        compare_loading_results(
            pandas_df,
            pandas_seconds,
            polars_df,
            polars_seconds,
        )
        print_data_quality(pandas_df, polars_df)
        clean_pandas_df = clean_with_pandas(pandas_df)
        clean_polars_df = clean_with_polars(polars_df)
        validate_cleaning_results(
            pandas_df,
            clean_pandas_df,
            clean_polars_df,
        )
        run_basic_eda(clean_pandas_df)
        create_age_distribution_charts(clean_pandas_df)
        education_summary = create_education_income_charts(clean_pandas_df)
        descriptive_statistics = calculate_descriptive_statistics(clean_pandas_df)
        correlation = calculate_correlation_matrix(clean_pandas_df)
        create_correlation_charts(correlation)
        t_test_results = run_hours_per_week_t_test(clean_pandas_df)
        model_metrics = train_evaluate_and_save_pipeline(clean_pandas_df)
        generate_report(
            pandas_df,
            clean_pandas_df,
            pandas_seconds,
            polars_seconds,
            descriptive_statistics,
            correlation,
            education_summary,
            t_test_results,
            model_metrics,
        )
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"데이터 다운로드 오류: {error}", file=sys.stderr)
        return 1
    except (FileNotFoundError, PermissionError, OSError, ValueError) as error:
        print(f"데이터 파일 처리 오류: {error}", file=sys.stderr)
        return 1
    except (pd.errors.ParserError, pl.exceptions.PolarsError) as error:
        print(f"CSV 파싱 오류: {error}", file=sys.stderr)
        return 1
    except AssertionError as error:
        print(f"결과 검증 오류: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
