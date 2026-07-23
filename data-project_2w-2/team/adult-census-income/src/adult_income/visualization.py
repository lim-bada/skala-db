"""Seaborn 정적 차트와 Plotly 인터랙티브 차트를 생성한다."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns

from adult_income.config import MIN_GROUP_SAMPLE_COUNT
from adult_income.console import get_logger, log_section

logger = get_logger(__name__)


def _prepare_output_directory(output_dir: Path) -> None:
    """차트 출력 폴더를 만들고 실제 디렉터리인지 확인한다."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        message = f"차트 출력 폴더를 만들 수 없습니다: {output_dir}"
        raise RuntimeError(message) from error
    if not output_dir.is_dir():
        raise NotADirectoryError(f"차트 출력 경로가 폴더가 아닙니다: {output_dir}")


def _save_matplotlib_chart(output_path: Path) -> None:
    """현재 Matplotlib Figure를 저장하고 성공 여부를 확인한다."""
    try:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
    except OSError as error:
        raise RuntimeError(f"정적 차트를 저장하지 못했습니다: {output_path}") from error
    finally:
        plt.close()


def create_seaborn_charts(
    dataframe: pd.DataFrame,
    correlation_matrix: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    """분포, 상관관계, 그룹 비교 정적 차트를 PNG로 저장한다."""
    if dataframe.empty:
        raise ValueError("차트를 생성할 데이터가 비어 있습니다.")
    _prepare_output_directory(output_dir)
    sns.set_theme(style="whitegrid")
    chart_paths: list[Path] = []

    plt.figure(figsize=(10, 6))
    sns.histplot(
        data=dataframe,
        x="age",
        hue="income",
        bins=30,
        kde=True,
        stat="density",
        common_norm=False,
        element="step",
    )
    plt.title("Age Distribution by Income Group")
    plt.xlabel("Age")
    plt.ylabel("Density")
    plt.tight_layout()
    distribution_path = output_dir / "01_seaborn_age_distribution.png"
    _save_matplotlib_chart(distribution_path)
    chart_paths.append(distribution_path)

    plt.figure(figsize=(11, 8))
    sns.heatmap(
        correlation_matrix,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=0.5,
    )
    plt.title("Correlation Heatmap")
    plt.tight_layout()
    correlation_path = output_dir / "02_seaborn_correlation_heatmap.png"
    _save_matplotlib_chart(correlation_path)
    chart_paths.append(correlation_path)

    plt.figure(figsize=(8, 6))
    sns.boxplot(
        data=dataframe,
        x="income",
        y="hours-per-week",
        hue="income",
        palette="Set2",
        legend=False,
    )
    plt.title("Weekly Working Hours by Income Group")
    plt.xlabel("Income Group")
    plt.ylabel("Hours per Week")
    plt.tight_layout()
    group_path = output_dir / "03_seaborn_hours_group_comparison.png"
    _save_matplotlib_chart(group_path)
    chart_paths.append(group_path)

    log_section(logger, "Seaborn 정적 차트 저장")
    for chart_path in chart_paths:
        logger.info("저장 완료: %s", chart_path)
    return chart_paths


def save_plotly_chart(figure: go.Figure, output_path: Path) -> None:
    """Plotly JavaScript를 공유하는 오프라인 HTML로 저장한다."""
    try:
        figure.write_html(output_path, include_plotlyjs="directory")
    except (OSError, ValueError) as error:
        message = f"인터랙티브 차트를 저장하지 못했습니다: {output_path}"
        raise RuntimeError(message) from error


def create_plotly_charts(
    dataframe: pd.DataFrame,
    correlation_matrix: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    """분포, 상관관계, 그룹 비교 인터랙티브 차트를 저장한다."""
    if dataframe.empty:
        raise ValueError("차트를 생성할 데이터가 비어 있습니다.")
    _prepare_output_directory(output_dir)
    chart_paths: list[Path] = []

    distribution_figure = px.histogram(
        dataframe,
        x="education-num",
        color="income",
        nbins=16,
        barmode="overlay",
        opacity=0.65,
        marginal="box",
        histnorm="probability",
        title="Education Years Distribution by Income Group",
        labels={
            "education-num": "Education Years",
            "income": "Income Group",
            "probability": "Probability",
        },
    )
    distribution_figure.update_layout(
        template="plotly_white",
        hovermode="x unified",
    )
    distribution_path = output_dir / "04_plotly_education_distribution.html"
    save_plotly_chart(distribution_figure, distribution_path)
    chart_paths.append(distribution_path)

    correlation_figure = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            colorscale="RdBu",
            zmin=-1,
            zmax=1,
            colorbar={"title": "Correlation"},
            hovertemplate=(
                "X: %{x}<br>Y: %{y}<br>Correlation: %{z:.3f}<extra></extra>"
            ),
        )
    )
    correlation_figure.update_layout(
        title="Interactive Correlation Heatmap",
        template="plotly_white",
        width=900,
        height=750,
    )
    correlation_path = output_dir / "05_plotly_correlation_heatmap.html"
    save_plotly_chart(correlation_figure, correlation_path)
    chart_paths.append(correlation_path)

    workclass_summary = dataframe.groupby("workclass", as_index=False).agg(
        high_income_rate=("income_label", "mean"),
        sample_count=("income_label", "size"),
    )
    excluded_groups = workclass_summary[
        workclass_summary["sample_count"] < MIN_GROUP_SAMPLE_COUNT
    ]["workclass"].tolist()
    workclass_summary = workclass_summary[
        workclass_summary["sample_count"] >= MIN_GROUP_SAMPLE_COUNT
    ].copy()
    workclass_summary["high_income_rate"] *= 100
    workclass_summary = workclass_summary.sort_values(
        "high_income_rate",
        ascending=False,
    )

    group_figure = px.bar(
        workclass_summary,
        x="workclass",
        y="high_income_rate",
        color="high_income_rate",
        color_continuous_scale="Blues",
        text_auto=".1f",
        custom_data=["sample_count"],
        title=(
            f"High-Income Rate by Workclass (Sample Size >= {MIN_GROUP_SAMPLE_COUNT})"
        ),
        labels={
            "workclass": "Workclass",
            "high_income_rate": "High-Income Rate (%)",
        },
    )
    group_figure.update_traces(
        hovertemplate=(
            "Workclass: %{x}<br>"
            "High-Income Rate: %{y:.2f}%<br>"
            "Sample Count: %{customdata[0]:,}"
            "<extra></extra>"
        )
    )
    group_figure.update_layout(
        template="plotly_white",
        xaxis_tickangle=-30,
        coloraxis_colorbar={"title": "Rate (%)"},
    )
    group_path = output_dir / "06_plotly_workclass_comparison.html"
    save_plotly_chart(group_figure, group_path)
    chart_paths.append(group_path)

    log_section(logger, "Plotly 인터랙티브 차트 저장")
    for chart_path in chart_paths:
        logger.info("저장 완료: %s", chart_path)
    if excluded_groups:
        logger.info("표본 %d개 미만 제외: %s", MIN_GROUP_SAMPLE_COUNT, excluded_groups)
    return chart_paths
