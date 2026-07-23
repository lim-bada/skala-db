"""데이터 검증부터 보고서 생성까지 전체 분석 순서를 조정한다."""

import pandas as pd

from adult_income.config import (
    DATA_MANIFEST_PATH,
    DATA_PATH,
    MODEL_METADATA_PATH,
    MODEL_PATH,
    OUTPUT_DIR,
    REPORT_PATH,
)
from adult_income.console import configure_logging, get_logger, log_section
from adult_income.data import (
    clean_data,
    compare_pandas_and_polars,
    validate_data_file,
)
from adult_income.eda import perform_eda
from adult_income.modeling import (
    save_model_metadata,
    train_and_evaluate_model,
)
from adult_income.reporting import generate_report
from adult_income.statistics import perform_statistical_analysis
from adult_income.visualization import (
    create_plotly_charts,
    create_seaborn_charts,
)

logger = get_logger(__name__)


def run_analysis() -> dict[str, object]:
    """Adult Census Income 분석 전체 과정을 순서대로 실행한다."""
    logger.info("1/8 원본 데이터 무결성을 검증합니다.")
    data_manifest = validate_data_file(DATA_PATH, DATA_MANIFEST_PATH)

    logger.info("2/8 Pandas와 Polars 로딩 결과를 비교합니다.")
    raw_dataframe, loading_results = compare_pandas_and_polars(DATA_PATH)
    expected_shape = (
        int(data_manifest["expected_rows"]),
        int(data_manifest["expected_columns"]),
    )
    if raw_dataframe.shape != expected_shape:
        raise ValueError(
            "원본 데이터 크기가 manifest의 예상값과 다릅니다: "
            f"{raw_dataframe.shape} != {expected_shape}"
        )

    logger.info("3/8 결측치와 중복값을 처리합니다.")
    dataframe, quality_results = clean_data(raw_dataframe)

    logger.info("4/8 탐색적 데이터 분석을 수행합니다.")
    eda_results = perform_eda(dataframe)

    correlation_matrix = eda_results["correlation_matrix"]
    if not isinstance(correlation_matrix, pd.DataFrame):
        raise TypeError("상관계수 결과가 Pandas DataFrame이 아닙니다.")

    logger.info("5/8 정적·인터랙티브 차트를 생성합니다.")
    seaborn_paths = create_seaborn_charts(
        dataframe,
        correlation_matrix,
        OUTPUT_DIR,
    )
    plotly_paths = create_plotly_charts(
        dataframe,
        correlation_matrix,
        OUTPUT_DIR,
    )
    logger.info("6/8 기술통계와 가설검정을 수행합니다.")
    statistical_results = perform_statistical_analysis(
        dataframe,
        correlation_matrix,
    )
    logger.info("7/8 분류 Pipeline을 학습하고 평가합니다.")
    modeling_results = train_and_evaluate_model(dataframe, MODEL_PATH)
    metadata_path = save_model_metadata(
        modeling_results,
        MODEL_METADATA_PATH,
        str(data_manifest["sha256"]),
    )
    modeling_results["metadata_path"] = metadata_path

    analysis_results = {
        "data_manifest": data_manifest,
        "loading": loading_results,
        "quality": quality_results,
        "eda": eda_results,
        "statistics": statistical_results,
        "modeling": modeling_results,
        "chart_paths": [*seaborn_paths, *plotly_paths],
    }
    logger.info("8/8 Markdown 보고서를 생성합니다.")
    generated_report_path = generate_report(
        dataframe,
        analysis_results,
        REPORT_PATH,
    )
    analysis_results["report_path"] = generated_report_path

    log_section(logger, "전체 분석 완료")
    logger.info(
        "정제된 데이터: %s행, %d열",
        f"{dataframe.shape[0]:,}",
        dataframe.shape[1],
    )
    logger.info("생성된 차트: %d개", len(analysis_results["chart_paths"]))
    logger.info("저장된 모델: %s", modeling_results["model_path"])
    logger.info("모델 메타데이터: %s", metadata_path)
    logger.info("생성된 보고서: %s", generated_report_path)
    return analysis_results


def main() -> None:
    """콘솔 실행 진입점."""
    configure_logging()
    try:
        run_analysis()
    except Exception as error:
        # 최상위 경계에서만 예외를 종료 코드로 바꾸고 상세 traceback을 기록한다.
        logger.exception("분석 실행에 실패했습니다: %s", error)
        raise SystemExit(1) from error
