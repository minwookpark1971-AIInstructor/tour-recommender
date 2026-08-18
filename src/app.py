"""F6: Streamlit 웹 화면. 선호를 고르면 추천 카드·지도·코스를 보여준다."""
import pathlib
import sys

# `streamlit run src/app.py` 로 실행하면 파이썬 검색 경로가 src/ 로 잡혀
# 아래 `from src.course import ...` 가 src/src/course.py 를 찾다가 실패한다.
# 그래서 import 보다 먼저 저장소 루트를 검색 경로에 넣는다.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd                                            # noqa: E402
import streamlit as st                                         # noqa: E402

from src.course import SLOTS, build_course                     # noqa: E402
from src.preprocess import get_visited, load_profiles, load_spots  # noqa: E402
from src.recommender import recommend_by_cf, recommend_by_content  # noqa: E402

THEMES = {"전체": None, "자연": "A01", "역사·문화": "A02", "맛집": "A05"}

st.set_page_config(page_title="공주 관광 추천", page_icon="🗺️", layout="wide")


@st.cache_data
def get_spots() -> pd.DataFrame:
    """관광지 표를 읽는다(화면에서는 캐시해 두고 재사용한다)."""
    return load_spots()


@st.cache_data
def get_profiles() -> pd.DataFrame:
    """가상 유저의 연령대·성별 프로필을 읽는다."""
    return load_profiles()


def filter_spots(spots: pd.DataFrame, cat1: str | None, only_gongju: bool) -> pd.DataFrame:
    """테마와 지역 조건으로 관광지를 걸러낸다."""
    out = spots if cat1 is None else spots[spots["cat1"] == cat1]
    if only_gongju and out["is_gongju"].any():
        out = out[out["is_gongju"]]
    return out


def show_cards(recs: list[dict], spots: pd.DataFrame) -> None:
    """추천 결과를 카드로 보여준다."""
    lookup = spots.set_index(spots["id"].astype(str))
    top = max((r["score"] for r in recs), default=1.0) or 1.0
    for col, rec in zip(st.columns(len(recs)), recs):
        with col:
            st.markdown(f"**{rec['title']}**")
            if rec["id"] in lookup.index:
                row = lookup.loc[rec["id"]]
                st.caption(row["addr"])
                st.caption(f"테마 {row['cat1']}")
            # 점수는 상대 비교용이므로 최고점을 별 5개로 잡는다
            st.write("⭐" * max(1, round(5 * rec["score"] / top)))
            st.caption(f"점수 {rec['score']:.3f}")


def show_map(rows: pd.DataFrame, size: int = 200) -> None:
    """좌표를 지도에 찍는다."""
    if rows.empty:
        st.info("지도에 표시할 좌표가 없습니다.")
        return
    st.map(rows[["lat", "lng"]].rename(columns={"lng": "lon"}), size=size)


def show_course(user_id: str, only_gongju: bool) -> None:
    """오전-점심-오후-저녁 코스를 타임라인으로 보여준다."""
    course = build_course(user_id, only_gongju=only_gongju)
    for col, slot in zip(st.columns(4), SLOTS):
        with col:
            st.markdown(f"### {slot}")
            st.markdown(f"**{course[slot]['title']}**")
            st.caption(course[slot]["addr"])

    km = course["_total_km"]
    if course.get("_over_limit"):
        # 기준을 못 맞췄으면 통과한 척하지 않는다
        st.warning(f"총 이동거리 {km} km — 기준 60km 를 넘었습니다. 음식점 후보가 부족합니다.")
    else:
        st.success(f"총 이동거리 {km} km (기준 60km 이하)")
    show_map(pd.DataFrame([course[s] for s in SLOTS]), size=250)


def sidebar(profiles: pd.DataFrame) -> tuple[str, str | None, bool]:
    """사이드바 입력을 받아 (유저, 테마코드, 공주만보기) 를 돌려준다."""
    st.sidebar.header("내 정보")
    age = st.sidebar.selectbox("연령대", ["전체"] + sorted(profiles["age_group"].unique()))
    gender = st.sidebar.selectbox("성별", ["전체"] + sorted(profiles["gender"].unique()))

    # 조건에 맞는 유저를 목록 앞으로 올리고 ★ 를 붙인다.
    # 목록에서 빼버리면 조합에 따라 후보가 1~2명까지 줄어 화면이 이상해진다.
    match = profiles
    if age != "전체":
        match = match[match["age_group"] == age]
    if gender != "전체":
        match = match[match["gender"] == gender]
    # 조건을 안 걸었으면 전원이 일치이므로 ★ 를 붙이지 않는다(전부 붙으면 의미가 없다)
    filtered = age != "전체" or gender != "전체"
    matched = set(match["user_id"]) if filtered else set()

    info = profiles.set_index("user_id")
    order = sorted(profiles["user_id"], key=lambda u: (u not in matched, u))
    label = (f"유저 선택 (조건 일치 {len(matched)}명 / 전체 {len(profiles)}명)"
             if filtered else f"유저 선택 ({len(profiles)}명)")
    user_id = st.sidebar.selectbox(
        label, order,
        format_func=lambda u: (f"{'★ ' if u in matched else ''}{u} · "
                               f"{info.loc[u, 'age_group']}대 {info.loc[u, 'gender']}"))
    if filtered and not matched:
        st.sidebar.caption("이 조건에 해당하는 가상 유저는 없습니다. 목록은 전체를 보여줍니다.")

    theme = st.sidebar.selectbox("선호 테마", list(THEMES))
    only_gongju = st.sidebar.checkbox("공주 지역만 보기", value=True)
    return user_id, THEMES[theme], only_gongju


def main() -> None:
    """사이드바 입력을 받아 추천 결과와 코스를 화면에 그린다."""
    spots = get_spots()
    user_id, cat1, only_gongju = sidebar(get_profiles())
    allowed = set(filter_spots(spots, cat1, only_gongju)["id"].astype(str))

    st.title("🗺️ AI 맞춤형 관광 추천")
    st.caption(f"관광지 {len(spots)}건 · {user_id} 방문이력 {len(get_visited(user_id))}건 "
               f"· 조건에 맞는 곳 {len(allowed)}건")

    st.subheader("① 나와 비슷한 사람이 좋아한 곳")
    # 카탈로그 전체를 받아 조건으로 거른다. k 를 60 같은 고정값으로 두면 조건에 맞는 곳이
    # 그 창 밖으로 밀려 화면이 통째로 비는 일이 생긴다(테마 '자연'에서 절반이 그랬다).
    cf = [r for r in recommend_by_cf(user_id, k=len(spots)) if r["id"] in allowed][:5]
    if not cf:
        st.warning("조건에 맞는 추천이 없습니다. 테마나 지역 조건을 풀어 보세요.")
    else:
        show_cards(cf, spots)
        show_map(spots[spots["id"].astype(str).isin([r["id"] for r in cf])])

    st.subheader("② 이 곳과 비슷한 곳 찾기")
    pool = filter_spots(spots, cat1, only_gongju)
    if pool.empty:
        st.warning("조건에 맞는 관광지가 없습니다.")
    else:
        picked = st.selectbox("기준 관광지", pool["title"].tolist())
        seed = str(pool.loc[pool["title"] == picked, "id"].iloc[0])
        # ① 과 같은 방식으로 넉넉히 받아 조건에 맞는 것만 고른다.
        # 바로 k=5 를 부르면 카탈로그 전체에서 뽑혀 지역·테마 조건이 무시된다.
        content = [r for r in recommend_by_content(seed, k=len(spots))
                   if r["id"] in allowed][:5]
        if not content:
            st.warning("조건에 맞는 비슷한 곳이 없습니다. 조건을 풀어 보세요.")
        else:
            show_cards(content, spots)

    st.subheader("③ 오늘의 여행 코스")
    show_course(user_id, only_gongju)


main()
