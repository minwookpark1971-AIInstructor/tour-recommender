#!/usr/bin/env python3
"""PreToolUse 훅 - API 키 하드코딩을 쓰기 단계에서 물리적으로 차단한다."""
import json, re, sys

# Windows 기본 인코딩(cp949)으로 내보내면 하네스가 UTF-8 로 읽어 한글이 깨진다.
# exit 2 의 목적은 이 메시지를 Claude 가 읽고 스스로 고치는 것이므로 반드시 UTF-8 로 맞춘다.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

try:
    payload = json.load(sys.stdin)
except Exception:
    sys.exit(0)

ti = payload.get("tool_input", {}) or {}
content = ti.get("content") or ti.get("new_string") or ""

PATTERNS = [
    # 키 이름 앞뒤 따옴표와 값 쪽 따옴표를 모두 선택적으로 둔다.
    # 이래야 params={"serviceKey": "..."} 와 URL 직접삽입 ?serviceKey=... 까지 잡힌다.
    # 값 문자셋에 _ 와 . 이 없어 os.getenv(...) 나 상수명 참조는 20자 문턱을 못 넘는다(오탐 방지).
    (r'["\']?serviceKey["\']?\s*[:=]\s*["\']?[A-Za-z0-9%+/=]{20,}', "TourAPI 서비스키가 코드에 하드코딩되었습니다."),
    (r'["\']?TOUR_API_KEY["\']?\s*[:=]\s*["\']?[A-Za-z0-9%+/=]{20,}', "API 키가 코드에 하드코딩되었습니다."),
    (r'["\'][A-Za-z0-9]{32,}%3D%3D["\']',            "인코딩된 인증키로 보이는 문자열이 있습니다."),
]

for pat, msg in PATTERNS:
    if re.search(pat, content):
        print(f"차단: {msg}\n"
              f"수정 방법: .env 에 TOUR_API_KEY 를 두고 "
              f"os.getenv('TOUR_API_KEY') 로 읽으세요.", file=sys.stderr)
        sys.exit(2)   # exit 2 = 도구 호출 차단 + 이 메시지를 Claude 에게 전달

sys.exit(0)
