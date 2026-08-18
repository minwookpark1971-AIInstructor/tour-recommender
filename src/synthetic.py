"""API 키가 없을 때 쓰는 합성 관광지 데이터.

실제 TourAPI 응답과 형식을 똑같이 맞춰, 키가 없는 학생도 실습을 끝까지 할 수 있게 한다.
실데이터가 아니므로 이 경로로 들어가면 data_loader 가 반드시 경고를 출력한다.
"""
import random

from src import config


# 합성 데이터용 테마 단어. 항목마다 단어를 조금씩 다르게 뽑아 TF-IDF 동점을 줄인다.
THEMES = {
    12: [("A01", "자연", ["산", "둘레길", "계곡", "숲", "전망", "폭포", "바위", "야생화"]),
         ("A01", "호수", ["호수", "물빛", "산책", "야경", "분수", "갈대", "저수지", "노을"]),
         ("A02", "유적", ["성곽", "왕릉", "유적", "역사", "답사", "고분", "석탑", "성벽"]),
         ("A02", "사찰", ["사찰", "불교", "고찰", "단풍", "명상", "범종", "대웅전", "석불"])],
    14: [("A02", "박물관", ["박물관", "전시", "유물", "해설", "체험", "기획전", "도록", "학예"]),
         ("A02", "미술관", ["미술관", "그림", "작품", "관람", "설치", "조각", "회화", "아트"])],
    39: [("A05", "한식", ["한식", "백반", "국밥", "정식", "밑반찬", "된장", "제육", "칼국수"]),
         ("A05", "카페", ["카페", "커피", "디저트", "베이커리", "브런치", "라떼", "테라스", "로스팅"]),
         ("A05", "분식", ["분식", "떡볶이", "김밥", "튀김", "간식", "순대", "어묵", "쫄면"])],
}
COUNTS = {12: 130, 14: 50, 39: 90}

# 시군별 대략적인 중심 좌표. 이름과 좌표가 어긋나면 이동거리가 거짓말이 된다.
SIGUNGU_CENTER = {
    "공주시": (36.4467, 127.1190), "부여군": (36.2757, 126.9100),
    "논산시": (36.1872, 127.0987), "천안시": (36.8151, 127.1139),
    "아산시": (36.7898, 127.0018), "보령시": (36.3333, 126.6128),
    "서산시": (36.7848, 126.4503),
}
OTHER_SIGUNGU = [s for s in SIGUNGU_CENTER if s != "공주시"]

# 지역명을 제목에 넣지 않는다. 넣으면 지역 정보가 원-핫과 텍스트에 이중으로 들어가
# 콘텐츠 유사도가 실제보다 좋아 보이는 착시가 생긴다.
NAME_PREFIX = ["고마", "금강", "계룡", "무령", "웅진", "백제", "솔뫼", "황새"]


def synthetic_spots(content_type_id: int) -> list[dict]:
    """API 키가 없을 때 쓰는 합성 관광지. 형식은 TourAPI 응답과 똑같이 맞춘다."""
    rng = random.Random(config.SEED + content_type_id)
    themes = THEMES[content_type_id]
    rows = []
    for i in range(COUNTS[content_type_id]):
        cat1, theme, words = themes[i % len(themes)]
        # 60% 는 공주에 둔다. 나머지는 다른 시군에 흩어 놓는다.
        sigungu = "공주시" if i % 10 < 6 else OTHER_SIGUNGU[i % len(OTHER_SIGUNGU)]
        center_lat, center_lng = SIGUNGU_CENTER[sigungu]
        lat = center_lat + rng.uniform(-0.06, 0.06)
        lng = center_lng + rng.uniform(-0.06, 0.06)

        picked = rng.sample(words, 5)
        rows.append({
            "contentid": f"9{content_type_id}{i:04d}",
            "contenttypeid": str(content_type_id),
            "title": f"{rng.choice(NAME_PREFIX)} {theme} {i:03d}",
            "addr1": f"충청남도 {sigungu} {theme}로 {i + 1}",
            "mapx": f"{lng:.6f}",
            "mapy": f"{lat:.6f}",
            "cat1": cat1,
            "cat2": f"{cat1}{(i % 3) + 1:02d}",
            "cat3": f"{cat1}{(i % 3) + 1:02d}{(i % 5) + 1:02d}",
            "firstimage": "",
            "overview": f"{theme} 명소. {' '.join(picked)}.",
        })
    return rows
