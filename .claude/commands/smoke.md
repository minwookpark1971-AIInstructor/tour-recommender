---
description: 추천 결과를 눈으로 확인한다 (유저 3명 x Top-5)
allowed-tools: Bash, Read, Task
---

!`python -m src.recommender --smoke 2>&1 | head -40`

위 출력을 보고 다음을 판단하라.

- 유저마다 결과가 다른가? (전부 같으면 인기순으로 붕괴한 것이다)
- 유사도 점수에 편차가 있는가? (전부 동일하면 벡터화 실패다)
- 추천된 곳이 사용자 선호 테마와 실제로 관련 있는가?

이상하면 원인을 찾아 수정하고, 정상이면 `rec-verifier` 서브에이전트로 넘겨 적대적 검증을 받아라.
