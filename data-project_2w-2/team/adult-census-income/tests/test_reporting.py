"""Markdown 변환 결과의 구조와 숫자 표현을 검증한다."""

import pandas as pd

from adult_income.reporting import dataframe_to_markdown


def test_dataframe_to_markdown() -> None:
    dataframe = pd.DataFrame({"metric": ["accuracy"], "value": [0.8125]})

    markdown = dataframe_to_markdown(dataframe, include_index=False)

    assert "| metric | value |" in markdown
    assert "| accuracy | 0.8125 |" in markdown
