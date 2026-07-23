"""
프로그램명: 실습 4 - 데이터 시각화 및 분석 파이프라인
작성자: 임해안
작성일: 2026-07-21

목적:
    sales_100k.csv를 이용해 EDA 시각화, 통계 검정, 머신러닝 Pipeline,
    인터랙티브 차트 저장을 단계별로 수행한다.

입력 데이터:
    sales_100k.csv

변경 이력:
    - 2026-07-21: 실습 4-1 EDA 시각화 4종(2×2 서브플롯) 구현
    - 2026-07-21: 실습 4-2 독립표본 t-test와 카이제곱 독립성 검정 구현
    - 2026-07-21: 실습 4-3 전처리·회귀 Pipeline 학습, 평가, 저장·재로딩 구현
    - 2026-07-21: 실습 4-4 지역·카테고리별 Plotly 차트 HTML 저장 구현
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import joblib
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import plotly.express as px
    import seaborn as sns
    from matplotlib import font_manager
    from scipy.stats import chi2_contingency, ttest_ind
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
except ImportError as error:
    package_name = error.name or "필수 패키지"
    raise SystemExit(
        f"'{package_name}' 패키지가 필요합니다. "
        "'.venv/bin/python -m pip install -r requirements.txt'를 실행하세요."
    ) from error


DATA_FILE = Path("sales_100k.csv")
EDA_FIGURE_FILE = Path("practice4_eda.png")
MODEL_FILE = Path("sales_amount_pipeline.joblib")
PLOTLY_CHART_FILE = Path("region_category_sales.html")
REQUIRED_COLUMNS = {
    "order_date",
    "region",
    "category",
    "payment_method",
    "quantity",
    "unit_price",
    "customer_age",
    "amount",
}
NUMERIC_COLUMNS = ["quantity", "unit_price", "customer_age", "amount"]
MODEL_NUMERIC_FEATURES = ["quantity", "unit_price", "customer_age"]
MODEL_CATEGORICAL_FEATURES = ["region", "category", "payment_method"]
MODEL_FEATURES = MODEL_NUMERIC_FEATURES + MODEL_CATEGORICAL_FEATURES
SIGNIFICANCE_LEVEL = 0.05
RANDOM_STATE = 42
TEST_SIZE = 0.2


# 실습 4-1: 시각화를 위한 한글 글꼴과 차트 스타일 설정
def configure_plot_style() -> None:
    """한글을 지원하는 글꼴을 선택하고 Seaborn 차트 스타일을 설정한다."""
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in ("AppleGothic", "Malgun Gothic", "NanumGothic"):
        if font_name in available_fonts:
            plt.rcParams["font.family"] = font_name
            break

    plt.rcParams["axes.unicode_minus"] = False
    sns.set_theme(style="whitegrid", font=plt.rcParams["font.family"])


# 실습 4 공통: CSV 로딩, 컬럼 검증, 결측치·IQR 이상치 정제
def load_and_clean_sales(data_file: Path) -> pd.DataFrame:
    """CSV를 로딩·검증하고 amount의 IQR 이상치와 분석 필수 결측치를 제거한다."""
    if not data_file.is_file():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {data_file}")

    df = pd.read_csv(data_file, encoding="utf-8-sig")
    if df.empty:
        raise ValueError("분석할 데이터 행이 없습니다.")

    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {sorted(missing_columns)}")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    amount = df["amount"].dropna()
    if amount.empty:
        raise ValueError("amount 컬럼에 분석 가능한 숫자 값이 없습니다.")

    q1 = amount.quantile(0.25)
    q3 = amount.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    clean_df = df.loc[
        df["amount"].between(lower_bound, upper_bound)
        & df["order_date"].notna()
        & df["region"].notna()
        & df["category"].notna()
    ].copy()
    if clean_df.empty:
        raise ValueError("결측치와 이상치를 제거한 후 분석할 데이터가 없습니다.")

    print(f"원본 데이터: {len(df):,}행")
    print(f"분석용 정제 데이터: {len(clean_df):,}행")
    return clean_df


# 실습 4-1: 히스토그램·박스플롯·월별 라인·상관 히트맵 생성
def create_eda_visualizations(df: pd.DataFrame, output_file: Path) -> None:
    """히스토그램·박스플롯·월별 라인·상관 히트맵을 2×2로 저장한다."""
    configure_plot_style()
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    sns.histplot(data=df, x="amount", bins=50, kde=True, ax=axes[0, 0])
    axes[0, 0].set_title("매출액 분포 (Histogram + KDE)")
    axes[0, 0].set_xlabel("매출액")
    axes[0, 0].set_ylabel("거래 건수")

    sns.boxplot(data=df, x="region", y="amount", ax=axes[0, 1])
    axes[0, 1].set_title("지역별 매출액 분포 (Box Plot)")
    axes[0, 1].set_xlabel("지역")
    axes[0, 1].set_ylabel("매출액")

    monthly_sales = (
        df.assign(month=df["order_date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)
        .agg(total=("amount", "sum"))
    )
    sns.lineplot(
        data=monthly_sales,
        x="month",
        y="total",
        marker="o",
        ax=axes[1, 0],
    )
    axes[1, 0].set_title("월별 총매출 추이 (Line Plot)")
    axes[1, 0].set_xlabel("월")
    axes[1, 0].set_ylabel("총매출")
    axes[1, 0].tick_params(axis="x", rotation=45)

    correlation_columns = [column for column in NUMERIC_COLUMNS if column in df.columns]
    if len(correlation_columns) < 2:
        raise ValueError("상관관계 분석에는 수치형 컬럼이 2개 이상 필요합니다.")
    correlation = df[correlation_columns].corr()
    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        ax=axes[1, 1],
    )
    axes[1, 1].set_title("수치형 변수 상관관계 (Heatmap)")

    fig.suptitle("Sales Data EDA", fontsize=18, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"EDA 시각화 저장 완료: {output_file}")


# 실습 4-2: 독립표본 t-test와 카이제곱 독립성 검정
def run_sales_t_test(df: pd.DataFrame) -> None:
    """서울과 부산의 평균 매출 차이를 Welch 독립표본 t-test로 검정한다."""
    seoul_amount = df.loc[df["region"] == "서울", "amount"].dropna()
    busan_amount = df.loc[df["region"] == "부산", "amount"].dropna()
    if len(seoul_amount) < 2 or len(busan_amount) < 2:
        raise ValueError("t-test를 수행하려면 서울과 부산 데이터가 각각 2건 이상 필요합니다.")

    t_statistic, p_value = ttest_ind(
        seoul_amount,
        busan_amount,
        equal_var=False,
        nan_policy="omit",
    )

    print("\n[실습 4-2-1] 서울 vs 부산 평균 매출 t-test")
    print(f"서울: {len(seoul_amount):,}건, 평균 {seoul_amount.mean():,.2f}")
    print(f"부산: {len(busan_amount):,}건, 평균 {busan_amount.mean():,.2f}")
    print(f"t-statistic: {t_statistic:.6f}")
    print(f"p-value: {p_value:.6g}")
    if p_value < SIGNIFICANCE_LEVEL:
        print("해석: p < 0.05이므로 두 지역의 평균 매출 차이는 통계적으로 유의미합니다.")
    else:
        print("해석: p >= 0.05이므로 두 지역의 평균 매출 차이가 유의미하다고 볼 근거가 부족합니다.")


def run_independence_chi_square_test(df: pd.DataFrame) -> None:
    """실습 3의 지역·카테고리 groupby 결과로 두 변수의 독립성을 검정한다."""
    region_category_counts = df.groupby(["region", "category"]).size()
    contingency_table = region_category_counts.unstack(fill_value=0)
    if contingency_table.shape[0] < 2 or contingency_table.shape[1] < 2:
        raise ValueError("카이제곱 검정에는 각 범주형 변수가 2개 이상의 범주를 가져야 합니다.")

    chi2_statistic, p_value, degrees_of_freedom, expected = chi2_contingency(
        contingency_table
    )

    print("\n[실습 4-2-2] region × category 카이제곱 독립성 검정")
    print("분할표:")
    print(contingency_table)
    print(f"chi2-statistic: {chi2_statistic:.6f}")
    print(f"degrees of freedom: {degrees_of_freedom}")
    print(f"p-value: {p_value:.6g}")
    print(f"최소 기대빈도: {expected.min():.2f}")
    if p_value < SIGNIFICANCE_LEVEL:
        print("해석: p < 0.05이므로 지역과 상품 카테고리는 서로 연관성이 있습니다.")
    else:
        print("해석: p >= 0.05이므로 지역과 상품 카테고리에 연관성이 있다고 볼 근거가 부족합니다.")


# 실습 4-3: 전처리·회귀 Pipeline 구성, 학습, 평가, 저장·재로딩
def build_sales_pipeline() -> Pipeline:
    """결측치 처리·스케일링·원핫 인코딩·선형회귀를 하나의 Pipeline으로 구성한다."""
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
            ("model", LinearRegression()),
        ]
    )


def train_save_and_reload_pipeline(df: pd.DataFrame, model_file: Path) -> None:
    """매출 예측 Pipeline을 학습·평가하고 joblib 저장 후 재로딩을 검증한다."""
    missing_features = set(MODEL_FEATURES) - set(df.columns)
    if missing_features:
        raise ValueError(f"모델 학습에 필요한 컬럼이 없습니다: {sorted(missing_features)}")

    model_data = df.dropna(subset=["amount"])
    if len(model_data) < 10:
        raise ValueError("모델 학습과 평가를 위해 유효 데이터가 10건 이상 필요합니다.")

    features = model_data[MODEL_FEATURES]
    target = model_data["amount"]
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    pipeline = build_sales_pipeline()
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    score = pipeline.score(x_test, y_test)

    print("\n[실습 4-3] sklearn Pipeline 학습·평가·저장")
    print(f"학습 데이터: {len(x_train):,}건")
    print(f"평가 데이터: {len(x_test):,}건")
    print(f"예측값 샘플: {[round(float(value), 2) for value in predictions[:5]]}")
    print(f"R² score: {score:.6f}")

    joblib.dump(pipeline, model_file)
    reloaded_pipeline = joblib.load(model_file)
    reloaded_predictions = reloaded_pipeline.predict(x_test.iloc[:5])
    maximum_difference = abs(predictions[:5] - reloaded_predictions).max()
    if maximum_difference > 1e-9:
        raise AssertionError("저장 전후 Pipeline의 예측 결과가 일치하지 않습니다.")

    reloaded_score = reloaded_pipeline.score(x_test, y_test)
    print(f"모델 저장 완료: {model_file}")
    print(f"재로딩 모델 R² score: {reloaded_score:.6f}")


# 실습 4-4: 지역·카테고리별 총매출 Plotly 차트 생성 및 HTML 저장
def create_interactive_sales_chart(df: pd.DataFrame, output_file: Path) -> None:
    """지역·카테고리별 총매출을 그룹 막대 차트로 만들고 HTML로 저장한다."""
    regional_category_sales = (
        df.groupby(["region", "category"], as_index=False)
        .agg(total=("amount", "sum"))
        .sort_values("total", ascending=False)
    )
    if regional_category_sales.empty:
        raise ValueError("Plotly 차트로 표현할 집계 데이터가 없습니다.")

    figure = px.bar(
        regional_category_sales,
        x="region",
        y="total",
        color="category",
        barmode="group",
        title="지역·카테고리별 총매출",
        labels={"region": "지역", "category": "카테고리", "total": "총매출"},
        hover_data={"total": ":,.0f"},
    )
    figure.update_layout(
        xaxis_title="지역",
        yaxis_title="총매출",
        legend_title="카테고리",
        hovermode="x unified",
    )
    figure.write_html(output_file, include_plotlyjs=True, full_html=True)
    print(f"\n[실습 4-4] Plotly 인터랙티브 차트 저장 완료: {output_file}")


# 실습 4-1부터 4-4까지 순차 실행
def main() -> int:
    """실습 4-1 시각화부터 4-4 인터랙티브 차트까지 순서대로 수행한다."""
    try:
        sales_df = load_and_clean_sales(DATA_FILE)
        create_eda_visualizations(sales_df, EDA_FIGURE_FILE)
        run_sales_t_test(sales_df)
        run_independence_chi_square_test(sales_df)
        train_save_and_reload_pipeline(sales_df, MODEL_FILE)
        create_interactive_sales_chart(sales_df, PLOTLY_CHART_FILE)
    except (
        FileNotFoundError,
        PermissionError,
        OSError,
        ValueError,
        AssertionError,
        pd.errors.ParserError,
    ) as error:
        print(f"실습 4 실행 오류: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
