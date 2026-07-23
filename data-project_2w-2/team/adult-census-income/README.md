# Adult Census Income 데이터 분석

Adult Census Income 데이터의 품질 처리, EDA, 시각화, 통계 검정,
LogisticRegression 학습과 Markdown 보고서 생성을 재현하는 프로젝트입니다.

## 1. 개발 환경

- Python 3.11
- 파일 인코딩: UTF-8
- Windows PowerShell 기준

패키지 버전은 `pyproject.toml`에 고정되어 있습니다.

## 2. 처음 실행하는 방법

프로젝트 폴더로 이동합니다.

```powershell
cd .\03차시-python\adult-census-income
```

Python 3.11 가상환경을 만들고 활성화합니다.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShell 실행 정책으로 활성화가 차단되면 현재 터미널에서만 완화합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

실행 패키지와 현재 프로젝트를 editable 모드로 설치합니다.

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

테스트와 Ruff까지 사용하려면 개발 의존성을 설치합니다.

```powershell
python -m pip install -r requirements-dev.txt
```

## 3. 데이터 확인

다음 두 파일이 있어야 합니다.

```text
data/adult.data
data/data_manifest.json
```

실행 시 `adult.data`의 파일 크기와 SHA-256을 manifest와 비교합니다. 데이터가
변경되거나 손상되면 분석을 중단합니다.

- 예상 크기: 32,561행, 15열
- 파일 크기: 3,974,305바이트
- SHA-256:
  `5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d`

## 4. 분석 실행

패키지를 설치한 뒤 다음 중 하나로 실행합니다.

```powershell
python main.py
```

```powershell
adult-income
```

## 5. 실행 결과

- `outputs/*.png`: Seaborn 정적 차트
- `outputs/*.html`: Plotly 인터랙티브 차트
- `models/adult_income_pipeline.joblib`: 학습된 전체 Pipeline
- `models/adult_income_pipeline.metadata.json`: 데이터·환경·평가 정보
- `report.md`: 실제 실행값으로 생성한 분석 보고서

joblib 파일은 scikit-learn 버전이 다르면 호환되지 않을 수 있습니다. 모델만
전달하지 말고 `pyproject.toml`, 데이터 manifest와 학습 코드를 함께 보관합니다.

## 6. 로컬 품질 검사

```powershell
ruff check src tests main.py
pytest
```

GitHub Actions나 외부 CI 연결은 포함하지 않습니다.

## 7. 폴더 구조

```text
adult-census-income/
├── .gitattributes
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── main.py
├── data/
│   ├── adult.data
│   └── data_manifest.json
├── src/
│   └── adult_income/
│       ├── __init__.py
│       ├── config.py
│       ├── console.py
│       ├── data.py
│       ├── eda.py
│       ├── visualization.py
│       ├── statistics.py
│       ├── modeling.py
│       ├── reporting.py
│       └── workflow.py
├── tests/
├── models/
└── outputs/
```

## 8. 모듈 역할

- `config.py`: 경로, 스키마, 난수와 분석 상수
- `data.py`: manifest 검증, Pandas·Polars 로딩, 정제
- `eda.py`: 데이터 구조와 그룹별 요약
- `visualization.py`: Seaborn·Plotly 차트
- `statistics.py`: 기술통계, 상관계수, Welch t-test
- `modeling.py`: Pipeline 학습·평가·모델 메타데이터
- `reporting.py`: Markdown 표와 `report.md`
- `workflow.py`: 전체 실행 순서

`__init__.py`는 `adult_income` 폴더를 명시적인 Python 패키지로 만들고 패키지
버전만 제공합니다. 재사용 함수는 필요한 모듈에서 직접 import합니다.
