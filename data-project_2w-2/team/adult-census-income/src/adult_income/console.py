"""프로젝트 전체에서 사용하는 콘솔 로깅 설정과 출력 도우미."""

import logging
import sys

LOGGER_NAME = "adult_income"


def configure_logging(level: int = logging.INFO) -> None:
    """UTF-8 콘솔 출력과 공통 로그 형식을 한 번만 설정한다."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        logger.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def get_logger(module_name: str) -> logging.Logger:
    """하위 모듈 이름을 포함하는 프로젝트 전용 로거를 반환한다."""
    return logging.getLogger(f"{LOGGER_NAME}.{module_name}")


def log_section(logger: logging.Logger, title: str) -> None:
    """로그에서 분석 단계의 시작점을 쉽게 찾도록 구분선을 출력한다."""
    logger.info("\n%s\n%s\n%s", "=" * 60, title, "=" * 60)
