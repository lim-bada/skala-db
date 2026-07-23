"""
프로그램명: 실습 2 - 파일 I/O, 예외 처리, Pydantic 검증 파이프라인
작성자: 임해안
작성일: 2026-7-20

목적:
    Python_Practice2_Data.json 원본 데이터를 읽고, 이후 생성할 CSV 파일을
    안전하게 다시 읽을 수 있도록 파일 I/O 기능을 준비한다.

변경 이력:
    - 2026-07-20: 실습 2-1 JSON 원본 로딩과 safe_load_csv() 구현 추가
    - 2026-07-20: 실습 2-2 Pydantic 스키마 및 2-3 검증 파이프라인 추가
    - 2026-07-20: 실습 2-4 검증 결과 CSV·JSON 저장 및 재로딩 검증 추가
    - 2026-07-20: 최종 예외 처리와 실패 종료 코드 추가
    - 2026-07-20: 실행 날짜별 debug·error 로그 파일 분리 저장 추가
"""

import csv
import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


LOGGER = logging.getLogger(__name__)
RAW_DATA_FILE = Path("Python_Practice2_Data.json")
MISSING_CSV_FILE = Path("__missing_practice2_input__.csv")
VALID_CSV_FILE = Path("valid_sales.csv")
ERROR_JSON_FILE = Path("validation_errors.json")
LOG_DIRECTORY = Path("logs")
LOG_DATE = date.today().isoformat()


def configure_logger():
    """콘솔·날짜별 디버그·날짜별 오류 로그를 중복 없이 설정한다."""
    if LOGGER.handlers:
        return

    LOG_DIRECTORY.mkdir(exist_ok=True)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    debug_handler = logging.FileHandler(
        LOG_DIRECTORY / f"debug_{LOG_DATE}.log",
        encoding="utf-8",
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(file_formatter)

    error_handler = logging.FileHandler(
        LOG_DIRECTORY / f"error_{LOG_DATE}.log",
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    LOGGER.addHandler(console_handler)
    LOGGER.addHandler(debug_handler)
    LOGGER.addHandler(error_handler)
    LOGGER.setLevel(logging.DEBUG)
    LOGGER.propagate = False


class SalesRecord(BaseModel):
    """월·지역·금액·선택 카테고리로 구성된 검증용 판매 레코드 스키마이다."""

    month: str = Field(min_length=1, description="비어 있지 않은 거래 월")
    region: str = Field(min_length=1, description="비어 있지 않은 거래 지역")
    amount: float = Field(gt=0, description="0보다 큰 거래 금액")
    category: Optional[str] = None

    @field_validator("month", "region")
    @classmethod
    def validate_not_blank(cls, value):
        """공백만 있는 문자열도 빈 값으로 판단해 거부한다."""
        if not value.strip():
            raise ValueError("빈 문자열 또는 공백만 사용할 수 없습니다.")
        return value


def safe_load_json(file_path):
    """실습 2의 원본 JSON 거래 데이터를 안전하게 읽어 리스트로 반환한다."""
    path = Path(file_path)

    try:
        with path.open("r", encoding="utf-8") as file:
            records = json.load(file)
        if not isinstance(records, list):
            raise ValueError("JSON 최상위 구조는 거래 목록(list)이어야 합니다.")

        LOGGER.info("원본 JSON 로딩 성공: %s (%d건)", path, len(records))
        return records
    except FileNotFoundError:
        LOGGER.error("원본 JSON 파일을 찾을 수 없습니다: %s", path)
        return None
    except json.JSONDecodeError as error:
        LOGGER.error("원본 JSON 형식이 올바르지 않습니다: %s", error)
        return None
    except (OSError, UnicodeDecodeError, ValueError) as error:
        LOGGER.error("원본 JSON 파일을 읽는 중 오류가 발생했습니다: %s", error)
        return None
    finally:
        print("로딩 종료\n")


def safe_load_csv(file_path):
    """
    CSV 파일을 UTF-8로 읽어 dict 리스트로 반환한다.

    파일이 없거나 읽기·인코딩·CSV 형식 오류가 나면 logger.error를 남기고
    None을 반환한다. 성공 시 logger.info를 남기며, 성공 여부와 관계없이
    finally 블록에서 '로딩 종료'를 출력한다.
    """
    path = Path(file_path)

    try:
        with path.open("r", encoding="utf-8", newline="") as file:
            records = list(csv.DictReader(file))
        LOGGER.info("CSV 로딩 성공: %s (%d건)", path, len(records))
        return records
    except FileNotFoundError:
        LOGGER.error("CSV 파일을 찾을 수 없습니다: %s", path)
        return None
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        LOGGER.error("CSV 파일을 읽는 중 오류가 발생했습니다: %s", error)
        return None
    finally:
        print("로딩 종료\n")


def run_schema_practice(raw_data):
    """실습 2-2: 실제 JSON 행과 의도적 오류 행으로 스키마를 검증한다."""
    print("\n[실습 2-2] Pydantic v2 스키마 정의")

    sample_record = SalesRecord.model_validate(raw_data[0])
    print("원본 JSON 샘플 검증 결과:", sample_record.model_dump())

    invalid_record = {
        "month": " ",
        "region": "",
        "amount": 0,
    }
    try:
        SalesRecord.model_validate(invalid_record)
    except ValidationError as error:
        print("ValidationError 오류 내용:")
        print(error)
    else:
        raise AssertionError("잘못된 판매 레코드에서 ValidationError가 발생해야 합니다.")


def build_validation_raw_data(source_data):
    """원본 JSON에서 4개 정상 행과 3개 오류 행으로 검증용 7건을 구성한다."""
    if len(source_data) < 7:
        raise ValueError("검증용 데이터를 만들려면 원본 거래가 7건 이상 필요합니다.")

    valid_rows = [dict(record) for record in source_data[:4]]
    valid_rows[3].pop("category", None)  # category가 없어도 유효한지 확인

    invalid_rows = [
        {**source_data[4], "month": " "},
        {**source_data[5], "region": ""},
        {**source_data[6], "amount": 0},
    ]
    return valid_rows + invalid_rows


def run_validation_pipeline(source_data):
    """실습 2-3: raw_data를 검증해 valid와 errors 목록으로 분리한다."""
    print("\n[실습 2-3] 검증 파이프라인: valid / errors 분리")

    raw_data = build_validation_raw_data(source_data)
    valid = []
    errors = []
    LOGGER.debug("검증용 raw_data %d건을 처리합니다.", len(raw_data))

    for row_number, row_data in enumerate(raw_data, start=1):
        try:
            record = SalesRecord.model_validate(row_data)
            valid.append(record.model_dump())
            LOGGER.debug("%d행 검증 성공", row_number)
        except ValidationError as error:
            error_message = str(error)
            errors.append({"row": row_number, "error": error_message})
            LOGGER.debug("%d행 검증 실패", row_number)
            print(f"{row_number}행 ValidationError:\n{error_message}")

    print(f"유효 레코드: {len(valid)}건")
    print(f"오류 레코드: {len(errors)}건")

    assert len(valid) == 4, "유효 레코드는 4건이어야 합니다."
    assert len(errors) == 3, "오류 레코드는 3건이어야 합니다."
    return valid, errors


def save_and_reload_results(valid, errors):
    """실습 2-4: 검증 결과를 저장하고 유효 CSV의 재로딩 건수를 확인한다."""
    print("\n[실습 2-4] 결과 파일 저장 + 재로딩 확인")
    LOGGER.debug("유효 %d건과 오류 %d건의 결과 파일 저장을 시작합니다.", len(valid), len(errors))

    try:
        with VALID_CSV_FILE.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(SalesRecord.model_fields))
            writer.writeheader()
            writer.writerows(valid)

        with ERROR_JSON_FILE.open("w", encoding="utf-8") as file:
            json.dump(errors, file, ensure_ascii=False, indent=2)
    except OSError as error:
        LOGGER.error("결과 파일을 저장하는 중 오류가 발생했습니다: %s", error)
        raise

    LOGGER.info("유효 레코드 CSV 저장 완료: %s (%d건)", VALID_CSV_FILE, len(valid))
    LOGGER.info("오류 레코드 JSON 저장 완료: %s (%d건)", ERROR_JSON_FILE, len(errors))

    reloaded = safe_load_csv(VALID_CSV_FILE)
    assert reloaded is not None, "저장한 유효 레코드 CSV를 다시 읽어야 합니다."
    assert len(reloaded) == 4, "재로딩한 유효 레코드는 4건이어야 합니다."

    print("재로딩 유효 레코드 수:", len(reloaded))
    print("결과 파일 저장 및 재로딩 검증을 통과했습니다!")


def main():
    """실습 2-1~4: 파일 I/O, 스키마, 검증, 결과 저장을 순서대로 실행한다."""
    configure_logger()

    try:
        print("[실습 2-1] 예외 처리 + 파일 읽기")
        source_data = safe_load_json(RAW_DATA_FILE)
        assert source_data is not None, "원본 JSON 파일을 정상적으로 읽어야 합니다."
        print("원본 JSON 거래 건수:", len(source_data))

        missing_result = safe_load_csv(MISSING_CSV_FILE)
        assert missing_result is None, "존재하지 않는 파일은 None을 반환해야 합니다."

        run_schema_practice(source_data)
        valid, errors = run_validation_pipeline(source_data)
        save_and_reload_results(valid, errors)
    except AssertionError as error:
        LOGGER.error("실습 결과 검증에 실패했습니다: %s", error)
        return 1
    except ValidationError as error:
        LOGGER.error("Pydantic 데이터 검증에 실패했습니다:\n%s", error)
        return 1
    except OSError as error:
        LOGGER.error("파일 처리 중 운영체제 오류가 발생했습니다: %s", error)
        return 1

    print("\n실습 2의 2-1~2-4 검증을 모두 통과했습니다!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
