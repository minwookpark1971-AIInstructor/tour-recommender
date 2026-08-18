"""F4: 협업 필터링 추천 - 나와 취향이 비슷한 사람이 좋아한 곳을 추천한다.

콘텐츠 기반 추천은 src/content_based.py 에 있다. 여기서는 결과만 다시 내보내
`from src.recommender import recommend_by_content` 형태가 그대로 동작하게 한다.
"""
import sys
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from src import config
from src.content_based import load_titles, recommend_by_content  # noqa: F401  (인수기준 인터페이스)
from src.preprocess import ensure_built, get_visited, load_ratings, load_spots


@lru_cache(maxsize=2)
def _rating_matrix_at(stamp: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """user x item 평점 행렬과 유저 간 유사도를 만든다. stamp 는 캐시 무효화용 수정시각이다."""
    r = load_ratings()
    # 안 본 곳은 0 이 아니라 NaN 으로 남긴다. 0 은 '싫어함'이라는 뜻이 되어버린다.
    mat = r.pivot_table(index="user_id", columns="item_id", values="rating")
    if mat.empty:
        # 빈 행렬을 cosine_similarity 에 넣으면 ValueError 가 난다
        return mat, pd.DataFrame()

    # 유저별 평균을 뺀 뒤(취향 편차만 남긴다) 빈칸을 0 으로 채워 유사도를 잰다
    centered = mat.sub(mat.mean(axis=1), axis=0).fillna(0.0)
    sim = pd.DataFrame(cosine_similarity(centered.to_numpy()),
                       index=mat.index, columns=mat.index)
    return mat, sim


def _rating_matrix() -> tuple[pd.DataFrame, pd.DataFrame]:
    """평점 행렬을 돌려준다. parquet 이 바뀌면 자동으로 다시 계산한다."""
    ensure_built()
    return _rating_matrix_at(config.RATINGS_PATH.stat().st_mtime_ns)


def _popular(k: int, exclude: set[str]) -> list[dict]:
    """인기순 폴백. 이력이 없는 새 유저에게 준다."""
    r = load_ratings()
    stat = r.groupby("item_id")["rating"].agg(["mean", "count"])
    # 평점이 높고 많이 방문된 곳일수록 위로 온다
    stat["score"] = stat["mean"] * np.log1p(stat["count"])
    # CF 점수(0~1 부근)와 자릿수를 맞춘다. 안 맞추면 콜드스타트 유저만 점수가 40배로 보인다.
    if len(stat) and stat["score"].max() > 0:
        stat["score"] = stat["score"] / stat["score"].max()
    stat = stat.drop(index=[i for i in exclude if i in stat.index])

    titles = load_titles()
    top = stat.sort_values("score", ascending=False).head(k)
    recs = [{"id": str(i), "title": str(titles.get(str(i), i)),
             "score": float(row["score"])} for i, row in top.iterrows()]

    # 평점이 한 번도 없는 곳은 위 집계에 아예 안 잡힌다. 모자라면 그런 곳으로 채운다.
    if len(recs) < k:
        seen = set(exclude) | {r["id"] for r in recs}
        for spot_id, title in titles.items():
            if len(recs) >= k:
                break
            if spot_id in seen:
                continue
            recs.append({"id": str(spot_id), "title": str(title), "score": 0.0})
    return recs[:k]


def recommend_by_cf(user_id: str, k: int = 5) -> list[dict]:
    """비슷한 취향의 유저가 좋아한 곳 Top-k 를 돌려준다. 방문한 곳은 뺀다."""
    k = max(0, int(k))
    mat, sim = _rating_matrix()
    user_id = str(user_id)

    if mat.empty:
        # 평점이 한 건도 없으면 유사도를 잴 수 없다. 예외 대신 인기순으로 돌려준다.
        return _popular(k, exclude=set())

    if user_id not in mat.index:
        # 콜드스타트 - 예외를 던지지 않고 인기순으로 돌려준다
        return _popular(k, exclude=set())

    visited = set(mat.columns[mat.loc[user_id].notna()].astype(str))
    neighbors = sim.loc[user_id].drop(index=user_id)

    centered = mat.sub(mat.mean(axis=1), axis=0).fillna(0.0)
    centered = centered.drop(index=user_id)
    weight = neighbors.to_numpy()

    denom = np.abs(weight).sum()
    if denom == 0:
        return _popular(k, exclude=visited)

    # 이웃의 취향 편차를 유사도로 가중평균해서 예측 점수를 만든다
    pred = pd.Series(weight @ centered.to_numpy() / denom, index=mat.columns)
    pred = pred.drop(index=[c for c in mat.columns if str(c) in visited])

    top = pred.sort_values(ascending=False).head(k)
    titles = load_titles()
    recs = [{"id": str(i), "title": str(titles.get(str(i), i)), "score": float(v)}
            for i, v in top.items()]

    # 후보가 모자라면 인기순으로 채운다 (카탈로그가 k 개 미만이면 그만큼만 나온다)
    if len(recs) < k:
        seen = visited | {r["id"] for r in recs}
        recs += _popular(k - len(recs), exclude=seen)
    return recs[:k]


def smoke() -> None:
    """유저 3명 x Top-5 를 표로 찍어 눈으로 확인한다."""
    for user_id in ["U001", "U002", "U_NEW_COLD"]:
        recs = recommend_by_cf(user_id, k=5)
        print(f"\n[{user_id}] 방문 {len(get_visited(user_id))}건")
        print(pd.DataFrame(recs).to_string(index=False))

    seed = str(load_spots()["id"].iloc[0])
    print(f"\n[콘텐츠 기반] 기준: {seed}")
    print(pd.DataFrame(recommend_by_content(seed, k=5)).to_string(index=False))


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        smoke()
    else:
        print("사용법: python -m src.recommender --smoke")
