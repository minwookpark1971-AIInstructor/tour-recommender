"""F5: 오전-점심-오후-저녁 4슬롯 여행 코스를 만든다."""
import sys

import pandas as pd

from src import config
from src.preprocess import (distances_km, get_visited, haversine_km,
                            load_ratings, load_spots)
from src.recommender import recommend_by_cf

SLOTS = ["오전", "점심", "오후", "저녁"]
MAX_TOTAL_KM = 60.0
SIGHT_TYPES = (12, 14)      # 관광지·문화시설
NEAR_CANDIDATES = 3         # 가까운 후보 몇 개 중에서 취향으로 고를지


def _preference(user_id: str) -> dict[str, float]:
    """유저가 준 평점을 소분류(cat3)별 평균으로 요약한다. 이력이 없으면 빈 dict 다."""
    ratings = load_ratings()
    mine = ratings[ratings["user_id"] == str(user_id)]
    if mine.empty:
        return {}
    spots = load_spots()[["id", "cat3"]].copy()
    spots["id"] = spots["id"].astype(str)
    merged = mine.merge(spots, left_on="item_id", right_on="id")
    return merged.groupby("cat3")["rating"].mean().to_dict()


def _as_slot(row: pd.Series) -> dict:
    """데이터프레임 한 줄을 코스 슬롯 하나로 바꾼다."""
    return {"id": str(row["id"]), "title": str(row["title"]),
            "lat": float(row["lat"]), "lng": float(row["lng"]),
            "addr": str(row["addr"]), "cat1": str(row["cat1"])}


def _pick_next(pool: pd.DataFrame, lat: float, lng: float,
               used: set[str], pref: dict[str, float]) -> pd.Series | None:
    """가까운 후보 몇 곳 중 유저 취향에 가장 맞는 곳을 고른다. 취향이 같으면 가까운 곳."""
    left = pool[~pool["id"].astype(str).isin(used)]
    if left.empty:
        return None
    left = left.assign(_dist=distances_km(lat, lng, left))
    near = left.nsmallest(min(NEAR_CANDIDATES, len(left)), "_dist")
    near = near.assign(_pref=near["cat3"].map(lambda c: pref.get(c, 0.0)))
    return near.sort_values(["_pref", "_dist"], ascending=[False, True]).iloc[0]


def _build_from(seed: pd.Series, sights: pd.DataFrame, foods: pd.DataFrame,
                avoid: set[str], pref: dict[str, float]) -> dict | None:
    """시작 관광지 하나를 받아 4슬롯을 이어붙인다. avoid 에 든 곳은 쓰지 않는다."""
    used = set(avoid) | {str(seed["id"])}
    course = {"오전": _as_slot(seed)}
    total, cur = 0.0, seed

    for slot, pool in [("점심", foods), ("오후", sights), ("저녁", foods)]:
        nxt = _pick_next(pool, cur["lat"], cur["lng"], used, pref)
        if nxt is None:
            return None
        total += haversine_km(cur["lat"], cur["lng"], nxt["lat"], nxt["lng"])
        course[slot] = _as_slot(nxt)
        used.add(str(nxt["id"]))
        cur = nxt

    course["_total_km"] = round(total, 2)
    return course


def _seed_order(user_id: str, sights: pd.DataFrame) -> pd.DataFrame:
    """코스 시작점 후보를 추천 순위대로 줄 세운다."""
    rec_ids = [r["id"] for r in recommend_by_cf(user_id, k=20)]
    # isin 은 추천 순서를 지키지 않으므로 순위를 직접 붙여 정렬한다.
    # 안 그러면 20순위가 1순위를 제치고 코스 시작점이 되어버린다.
    rank = {v: i for i, v in enumerate(rec_ids)}
    ranked = sights[sights["id"].astype(str).isin(rec_ids)].copy()
    ranked = ranked.assign(_rank=ranked["id"].astype(str).map(rank))
    # 공주 관광 서비스이므로 공주 후보를 먼저 본다. 다만 그 안에서는 CF 추천 순위를 지킨다.
    # 순위를 무시하면 개인화가 사라지고, 공주를 무시하면 하루 코스가 통째로 옆 시군으로 간다.
    ranked = ranked.sort_values(["is_gongju", "_rank"], ascending=[False, True])

    # 추천 후보로 60km 를 못 맞출 때를 대비한 예비 후보 (공주 시내는 서로 가깝다)
    spare = sights[sights["is_gongju"]]
    spare = spare if not spare.empty else sights
    both = pd.concat([ranked.drop(columns="_rank"), spare])
    return both.drop_duplicates(subset="id")


def build_course(user_id: str, only_gongju: bool = False) -> dict:
    """유저 추천을 바탕으로 하루 코스를 만든다. 방문한 곳은 빼고, 이동거리를 60km 이하로 맞춘다."""
    spots = load_spots()
    if only_gongju:
        # 화면에서 '공주 지역만 보기'를 켰으면 코스도 공주 안에서만 만든다.
        # 관광지와 음식점이 둘 다 있어야 4슬롯을 채울 수 있으므로 그때만 좁힌다.
        gj = spots[spots["is_gongju"]]
        if (gj["content_type_id"].isin(SIGHT_TYPES).any()
                and (gj["content_type_id"] == config.FOOD_TYPE).any()):
            spots = gj
    sights = spots[spots["content_type_id"].isin(SIGHT_TYPES)].copy()
    foods = spots[spots["content_type_id"] == config.FOOD_TYPE].copy()
    if sights.empty or foods.empty:
        raise ValueError("관광지 또는 음식점 데이터가 없습니다. preprocess 를 먼저 실행하세요.")

    visited = set(get_visited(user_id))
    pref = _preference(user_id)
    seeds = _seed_order(user_id, sights)

    best = None
    # 1차: 이미 방문한 곳을 모두 빼고 만든다. 2차: 후보가 모자라면 방문지도 허용한다.
    for avoid in (visited, set()):
        pick = seeds[~seeds["id"].astype(str).isin(avoid)]
        for _, seed in (pick if not pick.empty else seeds).iterrows():
            course = _build_from(seed, sights, foods, avoid, pref)
            if course is None:
                continue
            if course["_total_km"] <= MAX_TOTAL_KM:
                course["_over_limit"] = False
                return course
            if best is None or course["_total_km"] < best["_total_km"]:
                best = course
        if best is not None:
            break

    if best is None:
        raise ValueError("코스를 만들 후보가 부족합니다.")
    # 60km 를 못 맞췄으면 조용히 넘기지 않고 사실대로 표시한다
    best["_over_limit"] = True
    return best


def format_course(course: dict) -> str:
    """코스를 사람이 읽을 수 있는 표로 만든다."""
    rows = [{"슬롯": s, "이름": course[s]["title"], "주소": course[s]["addr"]} for s in SLOTS]
    warn = "  ← 60km 초과!" if course.get("_over_limit") else ""
    return (f"{pd.DataFrame(rows).to_string(index=False)}\n"
            f"총 이동거리: {course['_total_km']} km{warn}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "U001"
    print(f"[{target}] 여행 코스")
    print(format_course(build_course(target)))
