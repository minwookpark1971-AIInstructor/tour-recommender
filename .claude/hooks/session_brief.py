#!/usr/bin/env python3
"""SessionStart 훅 - 세션 시작/재개/컨텍스트압축 직후 현재 상태와 규칙을 재주입한다."""
import subprocess, sys, glob
from pathlib import Path

# Windows 기본 인코딩(cp949)으로 내보내면 하네스가 UTF-8 로 읽어 한글이 깨진다.
# exit 2 의 목적은 이 메시지를 Claude 가 읽고 스스로 고치는 것이므로 반드시 UTF-8 로 맞춘다.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

print("=== 프로젝트 현재 상태 ===")

proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no", "--no-header"],
                      capture_output=True, text=True)
tail = [l for l in (proc.stdout + proc.stderr).splitlines() if l.strip()][-2:]
print("테스트: " + (" | ".join(tail) if tail else "미실행"))

base = Path(".claude/.pass_baseline")
n = len(base.read_text(encoding="utf-8").split()) if base.exists() else 0
print(f"누적 통과(회귀 금지 대상): {n}개")
print(f"TourAPI 캐시: {len(glob.glob('data/raw/*.json'))}개 파일")

print("""
=== 잊지 말 것 ===
- Streamlit 만 사용, FastAPI/React 금지
- API 키는 .env + os.getenv()
- 테스트 파일 수정 금지, 구현을 고칠 것
- 파일당 200줄 초과 금지
- 추천 로직 변경 후에는 rec-verifier 서브에이전트로 검증
""")
