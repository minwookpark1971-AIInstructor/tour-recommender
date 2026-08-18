---
name: rec-algo
description: 콘텐츠 기반·협업 필터링 추천 알고리즘을 구현한다. 추천 로직 작성/수정, 유사도 계산, 여행 코스 생성 시 사용.
allowed-tools: Read, Write, Edit, Bash
---

# 추천 알고리즘 구현 규약

## A. 콘텐츠 기반 (Content-based)
- 피처: 카테고리(cat1/cat2/cat3) 원-핫 + 개요 TF-IDF + 지역 원-핫
- 유사도: `sklearn.metrics.pairwise.cosine_similarity`
- **자기 자신을 결과에서 반드시 제외** (argsort 후 `[1:]` 슬라이싱, 또는 id 필터)
- 서로 다른 스케일의 피처를 합치기 전에 정규화한다

## B. 협업 필터링 (Collaborative Filtering)
- user × item 평점 행렬 (`pivot_table`). 결측을 무조건 0으로 채우지 마라
  (0점 평가와 미평가는 다르다. 마스크를 따로 유지한다)
- 유저 기반 코사인 유사도 → 이웃 가중평균으로 예측
- **이미 방문한 항목 마스킹 필수**
- 콜드스타트(이력 0건) → 인기순 폴백. **예외를 던지지 마라.**

## C. 코스 생성
- 오전 / 점심 / 오후 / 저녁 4슬롯
- 점심·저녁 슬롯은 음식점(contentTypeId=39)에서 선택
- 슬롯 간 이동거리는 haversine 으로 계산, 총합 60km 초과 시 재선택
- 반환 dict 에 `_total_km` 키를 포함한다

## 금지 사항
- 유사도 계산 전 결측 처리를 건너뛰는 것 (NaN 이 전파되어 전부 nan 이 된다)
- 딥러닝 라이브러리 도입 (torch/tensorflow 금지 — 고등학생 대상, 3일)
- 결과가 비었을 때 빈 리스트를 조용히 반환하는 것 (폴백을 명시적으로 구현하라)

## 구현 후 필수
`python -m src.recommender --smoke` 로 유저 3명 × Top-5 를 표로 출력해 눈으로 확인한다.
그 다음 `rec-verifier` 서브에이전트를 호출해 적대적 검증을 받는다.
