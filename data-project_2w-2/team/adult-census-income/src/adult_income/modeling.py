"""전처리 Pipeline, LogisticRegression 학습·평가, 모델 저장 기능."""

import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from adult_income.config import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    RANDOM_STATE,
    TEST_SIZE,
)
from adult_income.console import get_logger, log_section

logger = get_logger(__name__)


def build_model_pipeline() -> Pipeline:
    """수치형·범주형 전처리와 LogisticRegression을 하나로 묶는다."""
    # 수치형과 범주형 변환을 Pipeline 안에 두면 학습·예측 시 동일하게 적용된다.
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=True,
                ),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    classifier = LogisticRegression(
        solver="liblinear",
        max_iter=1_000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )
    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def save_model_metadata(
    modeling_results: dict[str, object],
    metadata_path: Path,
    data_sha256: str,
) -> Path:
    """모델을 다시 만들 때 필요한 환경과 평가 정보를 JSON으로 저장한다."""
    metrics = modeling_results["metrics"]
    if not isinstance(metrics, dict):
        raise TypeError("모델 평가 지표 형식이 올바르지 않습니다.")

    metadata = {
        "model_type": "LogisticRegression",
        "model_file": Path(modeling_results["model_path"]).name,
        "data_sha256": data_sha256,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "package_versions": {
            package: version(package)
            for package in [
                "pandas",
                "scikit-learn",
                "scipy",
                "joblib",
            ]
        },
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "train_rows": modeling_results["train_size"],
        "test_rows": modeling_results["test_size"],
        "metrics": metrics,
        "reload_verified": modeling_results["reload_verified"],
    }
    try:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, TypeError, ValueError) as error:
        message = f"모델 메타데이터를 저장하지 못했습니다: {metadata_path}"
        raise RuntimeError(message) from error
    logger.info("모델 메타데이터 저장 완료: %s", metadata_path)
    return metadata_path


def train_and_evaluate_model(
    dataframe: pd.DataFrame,
    model_path: Path,
) -> dict[str, object]:
    """Pipeline을 학습·평가하고 joblib 파일로 저장한 뒤 재검증한다."""
    required_columns = {
        *NUMERIC_FEATURES,
        *CATEGORICAL_FEATURES,
        "income",
        "income_label",
    }
    missing_columns = required_columns - set(dataframe.columns)
    if missing_columns:
        raise ValueError(f"모델 학습에 필요한 열이 없습니다: {sorted(missing_columns)}")
    if dataframe.empty:
        raise ValueError("모델을 학습할 데이터가 비어 있습니다.")
    if dataframe["income_label"].nunique() != 2:
        raise ValueError("분류 모델 학습에는 income_label 두 클래스가 모두 필요합니다.")

    features = dataframe.drop(columns=["income", "income_label"])
    target = dataframe["income_label"]
    features_train, features_test, target_train, target_test = train_test_split(
        features,
        target,
        test_size=TEST_SIZE,
        stratify=target,
        random_state=RANDOM_STATE,
    )

    model_pipeline = build_model_pipeline()
    model_pipeline.fit(features_train, target_train)
    predictions = model_pipeline.predict(features_test)
    positive_probabilities = model_pipeline.predict_proba(features_test)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(target_test, predictions)),
        "precision": float(precision_score(target_test, predictions, zero_division=0)),
        "recall": float(recall_score(target_test, predictions, zero_division=0)),
        "f1": float(f1_score(target_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(target_test, positive_probabilities)),
    }
    confusion = pd.DataFrame(
        confusion_matrix(target_test, predictions),
        index=["Actual <=50K", "Actual >50K"],
        columns=["Predicted <=50K", "Predicted >50K"],
    )
    report = classification_report(
        target_test,
        predictions,
        target_names=["<=50K", ">50K"],
        output_dict=True,
        zero_division=0,
    )

    preprocessor = model_pipeline.named_steps["preprocessor"]
    classifier = model_pipeline.named_steps["classifier"]
    coefficients = pd.DataFrame(
        {
            "feature": preprocessor.get_feature_names_out(),
            "coefficient": classifier.coef_[0],
        }
    )
    positive_coefficients = coefficients.nlargest(10, "coefficient")
    negative_coefficients = coefficients.nsmallest(10, "coefficient")

    try:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_pipeline, model_path, compress=3)
        loaded_pipeline = joblib.load(model_path)
    except (OSError, EOFError, ValueError) as error:
        message = f"모델 파일을 저장하거나 다시 읽지 못했습니다: {model_path}"
        raise RuntimeError(message) from error
    loaded_predictions = loaded_pipeline.predict(features_test)
    reload_verified = bool((predictions == loaded_predictions).all())
    if not reload_verified:
        raise RuntimeError("저장 전후 Pipeline의 예측 결과가 다릅니다.")

    results = {
        "pipeline": model_pipeline,
        "model_path": model_path,
        "train_size": len(features_train),
        "test_size": len(features_test),
        "metrics": metrics,
        "confusion_matrix": confusion,
        "classification_report": report,
        "positive_coefficients": positive_coefficients,
        "negative_coefficients": negative_coefficients,
        "reload_verified": reload_verified,
    }

    log_section(logger, "LogisticRegression Pipeline 학습과 평가")
    logger.info("학습 데이터: %s행", f"{len(features_train):,}")
    logger.info("평가 데이터: %s행", f"{len(features_test):,}")
    logger.info("클래스 불균형 처리: class_weight='balanced'")
    logger.info("\n[평가 지표]")
    for metric_name, metric_value in metrics.items():
        logger.info("%s: %.4f", metric_name, metric_value)
    logger.info("\n[혼동행렬]\n%s", confusion)
    logger.info(
        "\n[분류 리포트]\n%s",
        classification_report(
            target_test,
            predictions,
            target_names=["<=50K", ">50K"],
            zero_division=0,
        ),
    )
    logger.info(
        "[>50K 예측 가능성을 높이는 주요 계수]\n%s",
        positive_coefficients.to_string(index=False),
    )
    logger.info(
        "\n[>50K 예측 가능성을 낮추는 주요 계수]\n%s",
        negative_coefficients.to_string(index=False),
    )
    logger.info("\n모델 저장 완료: %s", model_path)
    logger.info("저장 후 재로딩 예측 일치: %s", reload_verified)
    return results
