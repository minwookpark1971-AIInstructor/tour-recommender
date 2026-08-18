"""F1~F5 인수 기준 자동 검증.

이 파일은 수정하지 않는다. 실패하면 구현(src/)을 고쳐라.
아직 구현되지 않은 기능은 skip 되지 않고 실패한다 - 그것이 정상이다.
회귀 게이트(.claude/hooks/regression_gate.py)는 '한 번 통과한 테스트가 깨질 때'만 차단한다.
"""
import numpy as np
import pytest


# ---------- F1: 관광지 수집 ----------
def test_F1_관광지_150건_이상():
    import pandas as pd
    df = pd.read_parquet("data/processed/spots.parquet")
    assert len(df) >= 150, f"관광지 {len(df)}건 - 150건 이상 필요"


def test_F1_필수컬럼_결측_없음():
    import pandas as pd
    df = pd.read_parquet("data/processed/spots.parquet")
    cols = ["id", "title", "lat", "lng", "cat1"]
    missing = df[cols].isna().sum().sum()
    assert missing == 0, f"필수 컬럼 결측 {missing}건"


# ---------- F2: 사용자·방문이력 ----------
def test_F2_유저_50명_이상():
    import pandas as pd
    r = pd.read_parquet("data/processed/ratings.parquet")
    assert r["user_id"].nunique() >= 50


def test_F2_행렬_밀도_적정():
    import pandas as pd
    r = pd.read_parquet("data/processed/ratings.parquet")
    density = len(r) / (r["user_id"].nunique() * r["item_id"].nunique())
    assert 0.03 <= density <= 0.15, f"밀도 {density:.3f} - 3~15% 범위여야 함"


# ---------- F3: 콘텐츠 기반 ----------
def _seed_item():
    import pandas as pd
    return str(pd.read_parquet("data/processed/spots.parquet")["id"].iloc[0])


def test_F3_Top5_반환():
    from src.recommender import recommend_by_content
    assert len(recommend_by_content(_seed_item(), k=5)) == 5


def test_F3_자기자신_제외():
    from src.recommender import recommend_by_content
    seed = _seed_item()
    assert seed not in [str(r["id"]) for r in recommend_by_content(seed, k=5)]


def test_F3_유사도_붕괴_아님():
    from src.recommender import recommend_by_content
    scores = [r["score"] for r in recommend_by_content(_seed_item(), k=5)]
    assert np.std(scores) > 1e-6, "유사도가 전부 동일 - 벡터화 실패 의심"
    assert not any(np.isnan(s) for s in scores), "유사도에 NaN 포함"


# ---------- F4: 협업 필터링 ----------
def test_F4_Top5_반환():
    from src.recommender import recommend_by_cf
    assert len(recommend_by_cf("U001", k=5)) == 5


def test_F4_방문지_제외():
    from src.recommender import recommend_by_cf
    from src.preprocess import get_visited
    recs = {str(r["id"]) for r in recommend_by_cf("U001", k=5)}
    assert not (recs & {str(v) for v in get_visited("U001")}), "이미 방문한 곳을 추천함"


def test_F4_유저마다_결과_다름():
    from src.recommender import recommend_by_cf
    a = tuple(str(r["id"]) for r in recommend_by_cf("U001", k=5))
    b = tuple(str(r["id"]) for r in recommend_by_cf("U002", k=5))
    assert a != b, "모든 유저에게 동일 추천 - 인기순으로 붕괴함"


def test_F4_콜드스타트_폴백():
    from src.recommender import recommend_by_cf
    recs = recommend_by_cf("U_NEW_COLD", k=5)   # 이력 0건 신규 유저
    assert len(recs) == 5, "콜드스타트에서 폴백 실패"


# ---------- F5: 코스 생성 ----------
def test_F5_4슬롯():
    from src.course import build_course
    c = build_course("U001")
    for slot in ["오전", "점심", "오후", "저녁"]:
        assert slot in c and c[slot], f"{slot} 슬롯 누락"


def test_F5_이동거리_60km_이하():
    from src.course import build_course
    assert build_course("U001")["_total_km"] <= 60
