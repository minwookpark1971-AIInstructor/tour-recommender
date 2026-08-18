"""설정과 API 키를 한 곳에서만 읽는다. 다른 모듈은 여기만 import 한다."""
import os
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 최상위 폴더 - 어디서 실행하든 같은 곳을 가리키게 한다
ROOT = Path(__file__).resolve().parent.parent

# .env 는 반드시 프로젝트 폴더의 것을 읽는다. 경로를 안 주면 실행한 폴더 기준으로 찾다가
# 못 찾고도 조용히 넘어가서, 키가 있는데 합성 데이터로 도는 사고가 난다.
load_dotenv(ROOT / ".env")
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

SPOTS_PATH = PROCESSED_DIR / "spots.parquet"
RATINGS_PATH = PROCESSED_DIR / "ratings.parquet"

# TourAPI 기본값
API_BASE = "https://apis.data.go.kr/B551011/KorService2"
AREA_CODE = 34                      # 충청남도
# 공주시 시군구 코드. /areaCode2 를 실제로 호출해 확인한 값이다 (추측 아님).
# 지금은 충남 전역을 수집하고 주소로 공주를 가려내지만, 공주만 수집할 때 쓴다.
GONGJU_SIGUNGU_CODE = 1
CONTENT_TYPES = (12, 14, 39)        # 12=관광지, 14=문화시설, 39=음식점
FOOD_TYPE = 39                      # 점심·저녁 슬롯에 쓰는 콘텐츠타입
NUM_OF_ROWS = 100

# 공주 시내 중심 좌표 - 코스 생성과 합성 데이터의 기준점
GONGJU_LAT, GONGJU_LNG = 36.4467, 127.1190

# 이 서비스가 다루는 범위. 공주 중심 반경 30km 안쪽만 카탈로그로 삼는다.
# 카탈로그와 평점 범위를 다르게 두면 안 된다 - 추천은 공주권인데 코스는 천안으로 가는
# 식으로 층마다 범위가 어긋나고, 밀도 지표도 분모만 줄어 좋아 보이게 된다.
SERVICE_RADIUS_KM = 30

# 재현성을 위한 고정 시드. 바꾸면 가상 유저와 합성 데이터가 통째로 달라진다.
SEED = 20260824


def get_api_key() -> str | None:
    """TourAPI 디코딩 키를 환경변수에서 읽는다. 없으면 None 을 돌려준다."""
    key = os.getenv("TOUR_API_KEY", "").strip()
    # .env.example 의 안내 문구가 그대로 남아 있으면 키가 없는 것으로 본다
    if not key or key.startswith("여기에"):
        return None
    return key


def cache_path(area_code: int, content_type_id: int, page_no: int) -> Path:
    """TourAPI 응답을 저장할 캐시 파일 경로를 만든다."""
    return RAW_DIR / f"{area_code}_{content_type_id}_{page_no}.json"


def synthetic_path(content_type_id: int) -> Path:
    """합성 데이터 전용 캐시 경로. 실데이터 캐시와 파일명이 절대 겹치면 안 된다."""
    return RAW_DIR / f"synthetic_{content_type_id}.json"


def ensure_dirs() -> None:
    """데이터 폴더가 없으면 만든다."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
