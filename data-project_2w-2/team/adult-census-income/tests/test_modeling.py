"""분류 Pipeline의 구성과 주요 학습 설정을 검증한다."""

from adult_income.modeling import build_model_pipeline


def test_pipeline_contains_preprocessor_and_logistic_regression() -> None:
    model_pipeline = build_model_pipeline()

    assert list(model_pipeline.named_steps) == ["preprocessor", "classifier"]
    assert (
        model_pipeline.named_steps["classifier"].__class__.__name__
        == "LogisticRegression"
    )
    assert model_pipeline.named_steps["classifier"].class_weight == "balanced"
