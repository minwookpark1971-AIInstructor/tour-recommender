---
name: tourapi-fetch
description: 한국관광공사 TourAPI에서 관광지 데이터를 수집·캐싱한다. 관광 데이터 수집, TourAPI 호출, 관광지 목록 가져오기, areaBasedList 작업 시 사용.
allowed-tools: Read, Write, Edit, Bash
---

# TourAPI 수집 규약

## 인증
- 공공데이터포털(data.go.kr) → "한국관광공사_국문 관광정보 서비스" → 활용신청 → 인증키 발급
- 키는 `.env` 의 `TOUR_API_KEY`. 절대 하드코딩 금지.
- **디코딩(Decoding) 키**를 쓰고 `requests` 의 `params=` 로 넘긴다.
  (인코딩 키를 URL 문자열에 직접 붙이면 이중 인코딩으로 실패한다)

## 사용 오퍼레이션
| 용도 | 오퍼레이션 |
|---|---|
| 지역별 관광지 목록 | `areaBasedList` |
| 관광지 공통 상세(개요·이미지) | `detailCommon` |
| 콘텐츠 타입별 소개 | `detailIntro` |
| 연관 관광지 (콘텐츠기반 추천 보강) | 관광지별 연관 관광지 정보 API |

## 필수 파라미터
`serviceKey`, `MobileOS=ETC`, `MobileApp=TourRec`, `_type=json`, `numOfRows`, `pageNo`

지역 필터: `areaCode=34` (충청남도) → `sigunguCode` 로 공주시 지정
콘텐츠타입: 12=관광지, 14=문화시설, 39=음식점, 32=숙박

## 캐싱 규칙 (반드시 지킬 것)
1. 호출 전 `data/raw/{areaCode}_{contentTypeId}_{pageNo}.json` 존재 확인 → 있으면 **재호출하지 않는다**.
2. 응답은 **원본 그대로** 저장한다 (가공 후 저장 금지).
3. 실패 시 3회까지 지수 백오프 재시도 → 그래도 실패하면 캐시로 폴백하고 사용자에게 알린다.
4. `--refresh` 플래그가 명시적으로 주어질 때만 캐시를 무시한다.

> 캐시를 커밋해두면 수업 당일 API 장애·학교 방화벽·트래픽 초과 상황에서도
> 20명 전원이 오프라인으로 실습할 수 있다. 이건 규칙이 아니라 보험이다.

## 알려진 실패
- `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` → 키 발급 직후. 최대 1시간 대기 필요
- 응답이 XML 로 옴 → `_type=json` 파라미터 누락
- `totalCount` 는 있는데 `items` 가 빈 문자열 → 해당 페이지에 데이터 없음. 예외 아님, 정상 종료 처리
- 위경도(`mapx`, `mapy`)가 문자열로 옴 → float 캐스팅 필수, 실패 시 해당 행 제외

## 구현 후 확인
`python -m src.data_loader --stats` 로 수집 건수·결측률을 표로 출력한다.
