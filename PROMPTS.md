# 바이브코딩 실행 대본

Claude Code 에서 이 폴더를 열고, 채팅창에 아래 순서대로 입력하세요.
**순서를 건너뛰지 마세요.** `/` 로 시작하는 것은 Claude Code 채팅창의 슬래시 커맨드입니다.

---

## Step 0 — 환경 점검

```
requirements.txt 의 패키지를 설치해줘
```

```
/setup
```

TOUR_API_KEY 가 없다고 나오면:
1. https://www.data.go.kr → "한국관광공사_국문 관광정보 서비스" 검색 → 활용신청
2. 마이페이지 > 개발계정 > **일반 인증키(Decoding)** 복사
3. `.env.example` 을 `.env` 로 복사하고 키 붙여넣기
4. 다시 `/setup`

> 키 발급 직후 최대 1시간은 `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` 가 날 수 있습니다.

---

## Step 1 — 설계 먼저 (Plan mode)

`Shift+Tab` 을 눌러 **Plan mode** 로 전환한 뒤:

```
@tests/ACCEPTANCE.md 를 읽고 src/ 5개 모듈(data_loader, preprocess,
recommender, course, app)의 함수 시그니처와 데이터 흐름을 설계해줘.
ACCEPTANCE.md 의 "요구 인터페이스"를 정확히 지켜야 해. 코드는 아직 쓰지 마.
```

계획이 마음에 들면 승인하고 일반 모드로 나옵니다.

> **왜 Plan mode를 건너뛰면 안 되는가**: 설계 없이 바로 코딩시키면 모듈 간
> 컬럼명·반환형이 어긋납니다. recommender.py 가 preprocess.py 의 컬럼명을
> 지어내는 사고가 여기서 예방됩니다.

---

## Step 2 — 데이터 층 (F1·F2)

```
data-scout 서브에이전트로 TourAPI 응답 스펙을 먼저 확인해줘.
```
→ 원본 JSON 이 아니라 **필드 표 한 장**만 돌아옵니다 (컨텍스트 절약).

```
tourapi-fetch 스킬 규약대로 src/data_loader.py 를 구현해줘.
충남 areaCode=34, 공주시 시군구 필터. 캐싱 필수.
관광지(12)·문화시설(14)·음식점(39) 전부 수집해서 150건 이상 확보해줘.
```

```
src/preprocess.py 를 구현해줘.
spots.parquet 정제 + 가상 유저 50명 방문이력 생성. 행렬 밀도 3~15%.
get_visited() 도 함께.
```

```
/verify
```
→ F1·F2 가 PASS 되면 다음 단계로.

---

## Step 3 — 추천 엔진 (F3·F4) ★ 가장 중요

**여기서 반드시 `/clear` 하고 시작하세요.**
데이터 수집 단계의 API 응답 덩어리가 컨텍스트에 남아 있으면 추천 로직 품질이 떨어집니다.
`/clear` 해도 SessionStart 훅이 현재 상태와 규칙을 다시 브리핑해줍니다.

```
/clear
```

```
rec-algo 스킬 규약대로 src/recommender.py 의 콘텐츠 기반 추천부터 구현해줘.
recommend_by_content(item_id, k). 자기 자신 제외 반드시.
```

```
/smoke
```

```
협업 필터링 recommend_by_cf(user_id, k) 를 추가해줘.
방문지 마스킹 + 콜드스타트 인기순 폴백. 예외를 던지지 마.
```

```
rec-verifier 서브에이전트를 호출해서 지금 추천이 진짜 맞는지 반증해줘.
```
→ 이게 핵심입니다. 구현한 놈에게 검증을 맡기면 자기 코드라 통과시킵니다.

---

## Step 4 — 코스 생성 (F5)

```
src/course.py 를 구현해줘. build_course(user_id).
오전/점심/오후/저녁 4슬롯, 점심·저녁은 음식점(39)에서.
haversine 으로 총 이동거리 계산해서 _total_km 반환, 60km 초과하면 재선택.
```

---

## Step 5 — 웹앱 (F6)

```
/clear
```

```
src/app.py 를 Streamlit 으로 만들어줘.
사이드바: 연령대·성별·선호테마 선택
메인: 추천 카드 5개(이미지·이름·주소·점수) + st.map 지도 + 코스 타임라인
```

여기부터가 진짜 바이브코딩 구간입니다. 브라우저 띄워놓고 말로 고치세요.

```
카드 디자인을 학생들이 보기 좋게 개선해줘. 카드에 사진 크게, 점수는 별점으로.
```

```
지도에서 코스 순서대로 선을 이어줘.
```

---

## Step 6 — 배포 (F7)

```
/ship
```
→ 전부 통과하면 GitHub push → Streamlit Community Cloud 연결

---

## 막혔을 때

| 상황 | 조치 |
|---|---|
| 같은 오류를 3번 반복한다 | 대화를 이어가지 말고 `/clear` 후 오류 내용만 새로 제시 |
| 단계(Step)가 바뀐다 | `/clear` — 이전 단계 잔재 제거 |
| 규칙을 자꾸 어긴다 | 컨텍스트 드리프트. `/clear` 하면 훅이 규칙 재주입 |
| 조사·탐색이 필요하다 | 서브에이전트로 격리 (메인 컨텍스트 보호) |
| 되던 게 깨졌다 | 회귀 게이트가 이미 막았을 것. 메시지대로 구현을 고치면 됨 |

## Phase 2 (교안화)

`/verify` 에서 F1~F7 전부 PASS 된 뒤에 시작합니다.

```
lesson-splitter 서브에이전트로 src/ 를 3차시로 분해해줘.
```

그 전에는 손대지 마세요.
