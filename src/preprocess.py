"""F1·F2: 수집한 원본을 정제하고 가상 유저의 방문이력을 만든다."""
import math
import random
import sys

import numpy as np
import pandas as pd

from src import config
from src.data_loader import fetch_all, fetch_overviews

# 유저가 좋아할 수 있는 테마(cat1) 목록
CAT_POOL = ["A01", "A02", "A05"]
AGE_GROUPS = [10, 20, 30, 40, 50, 60]
GENDERS = ["여성", "남성"]


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이의 거리를 km 로 계산한다."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin(math.radians(lat2 - lat1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def distances_km(lat: float, lng: float, df: pd.DataFrame) -> np.ndarray:
    """한 지점에서 표의 모든 행까지 거리를 한 번에 계산한다(반복문보다 훨씬 빠르다)."""
    p1, p2 = math.radians(lat), np.radians(df["lat"].to_numpy())
    a = (np.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * np.cos(p2) * np.sin(np.radians(df["lng"].to_numpy() - lng) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def _to_float(value) -> float | None:
    """문자열로 오는 위경도를 실수로 바꾼다. 실패하면 None 이다."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_spots_table() -> pd.DataFrame:
    """원본을 정제해 관광지 표를 만들고 spots.parquet 으로 저장한다."""
    config.ensure_dirs()
    rows = []
    for r in fetch_all():
        lat, lng = _to_float(r.get("mapy")), _to_float(r.get("mapx"))
        # 위경도나 이름이 없는 행은 추천에 쓸 수 없으므로 버린다
        if lat is None or lng is None:
            continue
        title = (r.get("title") or "").strip()
        cat1 = (r.get("cat1") or "").strip()
        if not title or not cat1:
            continue
        addr = (r.get("addr1") or "").strip()
        rows.append({
            "id": str(r.get("contentid")),
            "title": title,
            "lat": lat,
            "lng": lng,
            "cat1": cat1,
            "cat2": (r.get("cat2") or "").strip(),
            "cat3": (r.get("cat3") or "").strip(),
            "addr": addr,
            "content_type_id": int(r.get("contenttypeid") or 0),
            "overview": (r.get("overview") or title).strip(),
            # 배포 화면은 https 라 http 이미지는 브라우저가 차단한다. https 로 바꾼다.
            "image": (r.get("firstimage") or "").strip().replace("http://", "https://"),
            "is_gongju": "공주" in addr,
        })

    df = pd.DataFrame(rows).drop_duplicates(subset="id").reset_index(drop=True)

    # 공주 중심 반경 안쪽만 남긴다. 카탈로그·평점·코스의 범위를 하나로 맞추기 위해서다.
    dist = distances_km(config.GONGJU_LAT, config.GONGJU_LNG, df)
    # 반경 안이 부족하면 전체로 건너뛰지 말고 5km 씩 넓힌다.
    # 한 번에 전체로 가면 카탈로그가 몇 배로 뛰어 평점 밀도(F2)가 엉뚱하게 깨진다.
    radius = config.SERVICE_RADIUS_KM
    while radius <= 60:
        near = df[dist <= radius]
        if len(near) >= 150:
            if radius != config.SERVICE_RADIUS_KM:
                print(f"[알림] 반경 {config.SERVICE_RADIUS_KM}km 로는 부족해 {radius}km 로 넓혔습니다.")
            df = near.reset_index(drop=True)
            break
        radius += 5
    else:
        print(f"[경고] 반경 60km 안에도 150건이 안 됩니다. 수집 범위를 확인하세요.")

    # areaBasedList2 는 개요를 주지 않는다. detailCommon2 로 따로 받아 채운다.
    overviews = fetch_overviews(df["id"].tolist())
    df["overview"] = [overviews.get(i) or t
                      for i, t in zip(df["id"], df["title"])]

    df = df.reset_index(drop=True)
    df.to_parquet(config.SPOTS_PATH, index=False)
    return df


def build_users(n: int = 50) -> pd.DataFrame:
    """가상 유저 n 명의 프로필과 방문이력을 만들고 ratings.parquet 으로 저장한다."""
    pool = load_spots()
    rng = random.Random(config.SEED)
    by_cat = {c: pool[pool["cat1"] == c]["id"].astype(str).tolist() for c in CAT_POOL}
    rows = []

    for i in range(1, n + 1):
        user_id = f"U{i:03d}"
        # 유저마다 1순위·2순위 취향이 다르다. 3종으로 찍어내면 협업필터링이
        # 너무 쉬운 문제를 푸는 셈이 되어 실제 성능을 과대평가하게 된다.
        primary = rng.choice(CAT_POOL)
        secondary = rng.choice([c for c in CAT_POOL if c != primary])
        rest = [c for c in CAT_POOL if c not in (primary, secondary)]

        plan = [(primary, rng.randint(6, 10), 5),
                (secondary, rng.randint(3, 5), 3)]
        if rest:
            plan.append((rest[0], rng.randint(1, 3), 2))

        age_group = rng.choice(AGE_GROUPS)
        gender = rng.choice(GENDERS)

        for cat, count, base in plan:
            cat_items = by_cat.get(cat, [])
            for item_id in rng.sample(cat_items, min(count, len(cat_items))):
                rows.append({
                    "user_id": user_id, "item_id": item_id,
                    "rating": min(5, max(1, base + rng.randint(-1, 0))),
                    "age_group": age_group, "gender": gender,
                })

    df = pd.DataFrame(rows).drop_duplicates(subset=["user_id", "item_id"])
    df = df.reset_index(drop=True)
    df.to_parquet(config.RATINGS_PATH, index=False)
    return df


def load_profiles() -> pd.DataFrame:
    """유저별 프로필(연령대·성별)만 한 줄씩 뽑아 돌려준다."""
    r = load_ratings()
    return r[["user_id", "age_group", "gender"]].drop_duplicates("user_id")


def ensure_built() -> None:
    """정제 산출물이 없으면 만든다. 있으면 아무 것도 하지 않는다."""
    if not config.SPOTS_PATH.exists():
        build_spots_table()
    if not config.RATINGS_PATH.exists():
        build_users()


def load_spots() -> pd.DataFrame:
    """정제된 관광지 표를 읽어온다."""
    if not config.SPOTS_PATH.exists():
        build_spots_table()
    return pd.read_parquet(config.SPOTS_PATH)


def load_ratings() -> pd.DataFrame:
    """방문이력(평점) 표를 읽어온다."""
    ensure_built()
    return pd.read_parquet(config.RATINGS_PATH)


def get_visited(user_id: str) -> list[str]:
    """해당 유저가 이미 방문한 관광지 id 목록을 돌려준다. 없으면 빈 리스트다."""
    r = load_ratings()
    return r.loc[r["user_id"] == str(user_id), "item_id"].astype(str).tolist()


def describe() -> str:
    """정제 결과 요약을 한 줄로 만든다."""
    spots, ratings = load_spots(), load_ratings()
    n_user = ratings["user_id"].nunique()
    n_item = ratings["item_id"].nunique()
    density = len(ratings) / (n_user * n_item)
    return (f"관광지 {len(spots)}건 (공주 {int(spots['is_gongju'].sum())}건) / "
            f"유저 {n_user}명 / 평점 {len(ratings)}건 / 밀도 {density:.3%}")


if __name__ == "__main__":
    build_spots_table()
    build_users(50)
    print(describe())
    if "--head" in sys.argv:
        print(load_spots().head(5).to_string())
