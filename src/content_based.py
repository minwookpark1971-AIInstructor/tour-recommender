"""F3: 콘텐츠 기반 추천 - 관광지의 카테고리와 설명이 얼마나 닮았는지로 추천한다."""
import re
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from src import config
from src.preprocess import ensure_built, load_spots

# 카테고리 블록과 줄거리 블록에 줄 가중치. 합이 1 이 되게 둔다.
W_CATEGORY, W_TEXT = 0.5, 0.5


def region_of(addr: str) -> str:
    """주소에서 시군 이름만 뽑는다. 못 찾으면 '기타' 다."""
    for token in str(addr).split():
        if token.endswith(("시", "군")):
            return token
    return "기타"


def clean_text(title: str, overview: str, region: str) -> str:
    """유사도 계산에 쓸 텍스트를 다듬는다. 지역명은 이미 원-핫에 있으므로 빼낸다."""
    text = f"{title} {overview}"
    text = re.sub(r"\[[^\]]*\]", " ", text)      # [유네스코 세계유산] 같은 꼬리표 제거
    for token in (region, region.rstrip("시군")):
        # 지역명을 남겨두면 원-핫과 텍스트에 이중으로 세어져 지역 정합성이 부풀려진다
        if token:
            text = text.replace(token, " ")
    return text


@lru_cache(maxsize=2)
def _content_matrix_at(stamp: int) -> tuple[pd.DataFrame, np.ndarray]:
    """관광지 특징 행렬과 코사인 유사도 행렬을 만든다. stamp 는 캐시 무효화용 수정시각이다."""
    df = load_spots()

    # 1) 카테고리 + 지역 + 콘텐츠타입 원-핫
    # 콘텐츠타입을 넣어야 "이 관광지와 비슷한 곳"에 식당이 섞이지 않는다.
    meta = df[["cat1", "cat2", "cat3"]].copy()
    meta["region"] = df["addr"].map(region_of)
    meta["ctype"] = df["content_type_id"].astype(str)
    cat = pd.get_dummies(meta).to_numpy(dtype=float)

    # 2) 이름·줄거리 TF-IDF
    # 한국어는 띄어쓰기가 적어 단어 단위로 자르면 제목 하나가 토큰 하나가 되어버린다.
    # 문자 2~3글자 단위로 잘라야 '갑사'와 '각원사'처럼 겹치는 부분이 잡힌다.
    text = [clean_text(t, o, region_of(a)) for t, o, a
            in zip(df["title"].fillna(""), df["overview"].fillna(""), df["addr"])]
    tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3),
                            min_df=2).fit_transform(text).toarray()

    # 3) 스케일이 다르므로 각 블록을 따로 정규화한 뒤 가중치를 주고 합친다
    features = np.hstack([normalize(cat) * W_CATEGORY,
                          normalize(tfidf) * W_TEXT])
    # NaN 이 남으면 유사도가 통째로 nan 이 되므로 여기서 확실히 없앤다
    features = np.nan_to_num(features)
    return df, cosine_similarity(features)


def content_matrix() -> tuple[pd.DataFrame, np.ndarray]:
    """콘텐츠 행렬을 돌려준다. parquet 이 바뀌면 자동으로 다시 계산한다."""
    ensure_built()   # 파일이 없으면 먼저 만든다. stat() 을 그냥 부르면 여기서 죽는다.
    return _content_matrix_at(config.SPOTS_PATH.stat().st_mtime_ns)


@lru_cache(maxsize=2)
def _titles_at(stamp: int) -> pd.Series:
    """관광지 id 로 이름을 찾는 표를 만든다."""
    df = load_spots()
    return df.set_index(df["id"].astype(str))["title"]


def load_titles() -> pd.Series:
    """id -> 이름 매핑. parquet 이 바뀌면 자동으로 다시 만든다."""
    ensure_built()
    return _titles_at(config.SPOTS_PATH.stat().st_mtime_ns)


def recommend_by_content(item_id: str, k: int = 5) -> list[dict]:
    """특정 관광지와 비슷한 곳 Top-k 를 돌려준다. 자기 자신은 빼고 준다."""
    k = max(0, int(k))   # 음수가 들어오면 슬라이싱이 엉뚱하게 동작한다
    df, sim = content_matrix()
    ids = df["id"].astype(str).tolist()
    if str(item_id) not in ids:
        raise ValueError(f"없는 관광지 id 입니다: {item_id}")

    pos = ids.index(str(item_id))
    scores = sim[pos]
    # 자기 자신은 점수를 낮추는 게 아니라 후보 목록에서 뺀다.
    # 점수만 -inf 로 두면 k 가 전체 개수 이상일 때 -inf 인 채로 결과에 들어온다.
    order = np.argsort(scores)[::-1]
    top = order[order != pos][:k]
    return [{"id": ids[i], "title": df["title"].iloc[i],
             "score": float(scores[i])} for i in top]
