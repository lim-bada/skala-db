"""파일 경로, 데이터 스키마, 실험 재현성 상수를 한곳에서 관리한다."""

from pathlib import Path

# src/adult_income/config.py를 기준으로 프로젝트 루트를 계산한다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "adult.data"
DATA_MANIFEST_PATH = PROJECT_ROOT / "data" / "data_manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / "adult_income_pipeline.joblib"
MODEL_METADATA_PATH = MODEL_DIR / "adult_income_pipeline.metadata.json"
REPORT_PATH = PROJECT_ROOT / "report.md"

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

NUMERIC_FEATURES = [
    "age",
    "fnlwgt",
    "education-num",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
]

CATEGORICAL_FEATURES = [
    "workclass",
    "education",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "native-country",
]

MISSING_COLUMNS = ["workclass", "occupation", "native-country"]
CORRELATION_COLUMNS = [*NUMERIC_FEATURES, "income_label"]
EXPECTED_INCOME_VALUES = {"<=50K", ">50K"}
INCOME_LABELS = {"<=50K": 0, ">50K": 1}

BENCHMARK_REPEATS = 5
MIN_GROUP_SAMPLE_COUNT = 100
SIGNIFICANCE_LEVEL = 0.05
TEST_SIZE = 0.2
RANDOM_STATE = 42
