---
description: 배포 전 최종 점검
allowed-tools: Bash, Read
---

배포 전 체크리스트를 순서대로 확인하고 결과를 표로 보고하라.

1. 테스트: !`python -m pytest tests/ -q --tb=no --no-header 2>&1 | tail -3`
2. .env 가 .gitignore 에 있는가: !`grep -c "^.env$" .gitignore`
3. 하드코딩된 키가 있는가: !`grep -rn "serviceKey" src/ 2>/dev/null || echo "없음"`
4. 앱 기동: !`timeout 25 streamlit run src/app.py --server.headless true 2>&1 | head -5`
5. requirements.txt 에 실제 import 한 패키지가 전부 있는가 (src/ 의 import 문과 대조하라)

하나라도 실패하면 **배포를 중단**하고 무엇을 고쳐야 하는지 알려라.
전부 통과하면 Streamlit Community Cloud 배포 절차를 단계별로 안내하라.
