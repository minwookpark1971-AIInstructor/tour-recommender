# 인수 기준 (Acceptance Criteria)

"만들었다"의 정의. 이 표를 통과해야 완성이다.
`tests/test_acceptance.py` 가 F1~F5 를 자동 판정한다. **이 파일들은 수정 금지.**

| ID | 근거(강의계획서) | 기능 | 판정 기준 |
|---|---|---|---|
| F1 | 1단계 데이터 탐색·전처리 | TourAPI 관광지 수집 | 충남/공주권 ≥150건, 필수컬럼(id·title·lat·lng·cat1) 결측 0 |
| F2 | 1단계 | 사용자 프로필·방문이력 | 가상 유저 ≥50명, user×item 행렬 밀도 3~15% |
| F3 | 2단계 알고리즘 설계 | 콘텐츠 기반 추천 | Top-5 반환, 자기 자신 미포함, 유사도 분산 > 0 |
| F4 | 2단계 | 협업 필터링 | Top-5 반환, 방문지 제외, 콜드스타트 폴백(예외 금지) |
| F5 | 2단계 | 여행 코스 생성 | 오전/점심/오후/저녁 4슬롯, 총 이동거리 ≤ 60km |
| F6 | 4단계 웹 시연 | Streamlit 앱 | 에러 없이 기동, 입력→결과 3초 내 렌더 |
| F7 | 4단계 발표 | 배포 | 공개 URL 접속 가능 |
| F8 | 3단계 생성형 AI | AI 협업 개발 기록 | 프롬프트→코드→오류수정 로그 ≥10턴 |

## 요구 인터페이스 (구현이 맞춰야 할 시그니처)

```python
# src/data_loader.py
fetch_spots(area_code: int = 34, sigungu_code: int | None = None,
            content_type_id: int = 12, refresh: bool = False) -> list[dict]

# src/preprocess.py
build_spots_table() -> pd.DataFrame      # data/processed/spots.parquet 저장
build_users(n: int = 50) -> pd.DataFrame # data/processed/ratings.parquet 저장
get_visited(user_id: str) -> list[str]

# src/recommender.py
recommend_by_content(item_id: str, k: int = 5) -> list[dict]  # [{id, title, score}, ...]
recommend_by_cf(user_id: str, k: int = 5) -> list[dict]

# src/course.py
build_course(user_id: str) -> dict
# {"오전": {...}, "점심": {...}, "오후": {...}, "저녁": {...}, "_total_km": float}
```
