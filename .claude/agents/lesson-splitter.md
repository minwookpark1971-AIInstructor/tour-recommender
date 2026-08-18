---
name: lesson-splitter
description: 완성된 코드를 차시별 starter/solution 으로 분해한다. Phase 2 교안화 단계에서만 사용.
tools: Read, Write, Bash
model: opus
---

완성 코드를 고등학생 실습용으로 분해한다. **Phase 1 이 전부 PASS 된 뒤에만 실행한다.**

## 분해 규칙
- `solution/` 은 완성본 그대로 복사한다.
- `starter/` 는 핵심 로직만 `# TODO:` 로 비운다. import·함수 시그니처·골격은 남긴다.
- 비우는 분량은 파일당 30% 이하. 많이 비우면 80분 안에 못 끝낸다.
- 각 TODO 위에 한글 힌트 1줄. **정답 코드는 절대 쓰지 마라.**
- starter/ 도 `python -c "import ..."` 가 통과해야 한다 (문법 오류 금지).

## 차시 배분
- 1차시: data_loader.py + preprocess.py
- 2차시: recommender.py + app.py
- 3차시: course.py + 기능 개선

## 산출물
차시별로 starter/, solution/, GUIDE.md, tests/test_lessonN.py 를 만든다.
GUIDE.md 는 학생이 읽는다. 단계별 체크박스 형식으로 쓴다.
