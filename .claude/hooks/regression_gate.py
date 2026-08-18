#!/usr/bin/env python3
"""PostToolUse 훅 - 회귀 게이트.

아직 구현 안 된 기능의 테스트가 실패하는 것은 허용한다(개발 초기엔 전부 빨강이므로).
그러나 '한 번이라도 통과했던 테스트'가 깨지면 exit 2 로 차단한다.
=> 앞으로만 가고 뒤로는 못 간다.
"""
import json, subprocess, sys, os
from pathlib import Path

# Windows 기본 인코딩(cp949)으로 내보내면 하네스가 UTF-8 로 읽어 한글이 깨진다.
# exit 2 의 목적은 이 메시지를 Claude 가 읽고 스스로 고치는 것이므로 반드시 UTF-8 로 맞춘다.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

fp = (payload.get("tool_input", {}) or {}).get("file_path", "") or ""
if "src" not in fp.replace("\\", "/") or not fp.endswith(".py"):
    sys.exit(0)

BASE = Path(".claude/.pass_baseline")
BASE.parent.mkdir(parents=True, exist_ok=True)

proc = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=line", "-q", "-rA", "--no-header"],
    capture_output=True, text=True,
)
out = proc.stdout + proc.stderr
passed = {l.split()[1] for l in out.splitlines()
          if l.startswith("PASSED ") and len(l.split()) > 1}

old = set(BASE.read_text(encoding="utf-8").split()) if BASE.exists() else set()
regressed = sorted(old - passed)

if regressed:
    print("회귀 발생 - 되던 테스트가 깨졌습니다. 다음 작업으로 넘어가지 마세요.", file=sys.stderr)
    for t in regressed:
        print(f"  X {t}", file=sys.stderr)
    print("\n(테스트 파일을 고치지 말고 구현을 고치세요)", file=sys.stderr)
    print("\n".join(out.splitlines()[-15:]), file=sys.stderr)
    sys.exit(2)

BASE.write_text("\n".join(sorted(passed)), encoding="utf-8")
if passed:
    print(f"[게이트 통과] 누적 통과 테스트 {len(passed)}개")
sys.exit(0)
