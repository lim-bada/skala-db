"""통계 효과크기 해석의 경계값을 검증한다."""

from adult_income.statistics import describe_effect_size


def test_effect_size_description() -> None:
    assert describe_effect_size(0.10) == "매우 작음"
    assert describe_effect_size(0.30) == "작음"
    assert describe_effect_size(0.60) == "중간"
    assert describe_effect_size(0.90) == "큼"
