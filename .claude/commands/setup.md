---
description: 개발 환경과 API 키 설정을 점검한다
allowed-tools: Bash, Read, Write
---

환경 점검 결과:

- Python: !`python --version`
- 설치된 패키지: !`python -m pip list 2>/dev/null | grep -Ei "pandas|scikit|streamlit|requests|pytest" || echo "미설치"`
- .env 존재: !`test -f .env && echo "있음" || echo "없음"`
- 캐시 파일: !`ls data/raw/*.json 2>/dev/null | wc -l`

위 결과를 보고 필요한 조치를 순서대로 수행하라.

1. 누락된 패키지가 있으면 `pip install -r requirements.txt` 실행
2. `.env` 가 없으면 `.env.example` 을 복사해 만들고, 사용자에게 TOUR_API_KEY 를 넣으라고 안내
3. 키가 설정되어 있으면 TourAPI 를 1건만 호출해 인증이 실제로 되는지 확인
4. 최종적으로 준비 완료 / 미완료를 표로 보고

키가 없다고 해서 임의의 더미 키를 넣지 마라.
