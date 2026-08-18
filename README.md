# AI 맞춤형 관광 추천 서비스 — 하네스 스캐폴드

공주정보고 경영정보과 3차시 프로젝트 (2026.8.24~26) · Phase 1 완성본 개발용

## 시작하는 법

이 zip 을 원하는 위치에 압축 해제하면 `tour-recommender` 폴더가 생깁니다.
**그 폴더를 Claude Code 의 작업 폴더로 열면 끝입니다.**

- Claude Code 데스크톱 앱 / VS Code 확장: **폴더 열기 → `tour-recommender` 선택**
- 터미널에서 쓰는 경우: `cd tour-recommender` 후 `claude`

작업 폴더로 열리는 순간 이 폴더의 `CLAUDE.md`, `.claude/settings.json`,
훅·스킬·서브에이전트·슬래시커맨드가 **자동으로 로드**됩니다.
따로 업로드하거나 채팅창에 붙여넣을 것이 없습니다.

폴더를 연 다음, Claude Code 채팅창에 이렇게 치세요:

```
requirements.txt 의 패키지를 설치해줘
```

그 다음부터는 `PROMPTS.md` 를 순서대로 따라가면 됩니다.
`/setup`, `/smoke`, `/verify`, `/ship` 은 **Claude Code 채팅창에 입력하는 슬래시 커맨드**입니다
(터미널 명령이 아닙니다).

## 이 스캐폴드에 들어있는 것

```
CLAUDE.md                    프로젝트 헌법 (항상 로드됨)
PROMPTS.md                   바이브코딩 실행 대본 ← 여기부터 시작
.claude/
  settings.json              권한 + 훅 등록
  hooks/
    guard_secrets.py         API 키 하드코딩을 쓰기 단계에서 차단 (exit 2)
    regression_gate.py       되던 테스트가 깨지면 차단 (회귀 게이트)
    session_brief.py         세션 시작·컨텍스트압축 후 규칙 재주입
  agents/
    data-scout.md            TourAPI 스펙 조사 (컨텍스트 격리)
    rec-verifier.md          추천 결과 적대적 검증 ★ 가장 중요
    lesson-splitter.md       Phase 2 교안화용
  skills/
    tourapi-fetch/SKILL.md   TourAPI 호출·캐싱 규약
    rec-algo/SKILL.md        추천 알고리즘 구현 규약
  commands/
    /setup   환경 점검
    /smoke   추천 결과 눈으로 확인
    /verify  인수기준 F1~F7 전체 검증
    /ship    배포 전 최종 점검
tests/
  ACCEPTANCE.md              인수 기준 + 요구 인터페이스
  test_acceptance.py         F1~F5 자동 판정 (수정 금지)
src/                         ← 여기를 클로드코드가 채운다
data/raw/                    TourAPI 캐시 (커밋할 것 = 오프라인 보험)
```

## 회귀 게이트가 동작하는 방식

처음에는 모든 테스트가 실패합니다. **정상입니다.**
게이트는 "전부 통과"를 요구하지 않고, **한 번이라도 통과했던 테스트가 깨지는 것**만 차단합니다.

```
코드 수정 → PostToolUse 훅 → pytest 실행
                              ├ 새 테스트 실패    → 통과 (개발 중이니까)
                              └ 되던 테스트 실패  → exit 2 차단 + Claude 자가수정
```

앞으로만 가고 뒤로는 못 갑니다.

## Windows 사용자 참고

훅은 bash 가 아니라 **Python 스크립트**로 작성되어 있어 Windows에서도 그대로 동작합니다.
`python` 명령이 PATH 에 있어야 합니다 (`python --version` 으로 확인).
`py` 만 되는 환경이면 `.claude/settings.json` 의 `python` 을 `py` 로 바꾸세요.

## Phase 2 (교안화)는 나중에

Phase 1 이 `/verify` 에서 전부 PASS 된 뒤에 `lesson-splitter` 로 3차시 분해를 시작합니다.
지금은 손대지 마세요.
