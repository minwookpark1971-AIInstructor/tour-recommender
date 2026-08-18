"""F1: TourAPI 에서 관광지를 수집하고 data/raw/ 에 캐싱한다."""
import json
import sys
import time

import requests

from src import config
from src.synthetic import synthetic_spots

def _request_page(key: str, area_code: int, sigungu_code: int | None,
                  content_type_id: int, page_no: int) -> dict:
    """TourAPI 한 페이지를 호출한다. 3회까지 지수 백오프로 재시도한다."""
    params = {
        "serviceKey": key, "MobileOS": "ETC", "MobileApp": "TourRec",
        "_type": "json", "numOfRows": config.NUM_OF_ROWS, "pageNo": page_no,
        "areaCode": area_code, "contentTypeId": content_type_id,
        "arrange": "A",
    }
    if sigungu_code is not None:
        params["sigunguCode"] = sigungu_code

    last = None
    for attempt in range(3):
        try:
            res = requests.get(f"{config.API_BASE}/areaBasedList2",
                               params=params, timeout=15)
            res.raise_for_status()
            # XML 이 오면 _type=json 이 안 먹은 것이므로 에러로 본다
            return res.json()
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"TourAPI 호출 실패(3회): {last}")


def _items_of(payload: dict) -> list[dict]:
    """TourAPI 응답에서 항목 리스트만 꺼낸다. 결과 0건이면 빈 리스트다."""
    body = payload.get("response", {}).get("body", {})
    items = body.get("items")
    # totalCount 는 있는데 items 가 빈 문자열인 경우가 정상적으로 존재한다
    if not isinstance(items, dict):
        return []
    item = items.get("item", [])
    return item if isinstance(item, list) else [item]


def _load_real_cache(area_code: int, content_type_id: int) -> list[dict]:
    """이미 받아둔 실데이터 캐시를 읽는다. 없으면 빈 리스트다."""
    rows, page_no = [], 1
    while True:
        path = config.cache_path(area_code, content_type_id, page_no)
        if not path.exists():
            break
        rows.extend(_items_of(json.loads(path.read_text(encoding="utf-8"))))
        page_no += 1
    return rows


def fetch_spots(area_code: int = config.AREA_CODE, sigungu_code: int | None = None,
                content_type_id: int = 12, refresh: bool = False) -> list[dict]:
    """지역·콘텐츠타입별 관광지 목록을 가져온다. 캐시가 있으면 재호출하지 않는다."""
    config.ensure_dirs()
    key = config.get_api_key()

    # 캐시를 키보다 먼저 본다. 순서를 반대로 하면 배포 서버(키 없음)에서
    # 커밋해 둔 실데이터 캐시를 놔두고 합성 데이터를 만들어버린다.
    cached = _load_real_cache(area_code, content_type_id)
    if cached and not refresh:
        return cached

    if key is None:
        # 키도 캐시도 없을 때만 합성 데이터로 간다. 조용히 넘어가지 않고 반드시 알린다.
        print(f"[경고] TOUR_API_KEY 도 캐시도 없어 합성 데이터를 사용합니다 "
              f"(contentTypeId={content_type_id}). 실데이터가 아닙니다.")
        rows = synthetic_spots(content_type_id)
        # 실데이터 캐시와 다른 이름으로 저장한다. 같은 이름을 쓰면 나중에 키를 넣어도
        # "캐시가 있다"며 합성 데이터를 실데이터로 착각해 읽는다.
        config.synthetic_path(content_type_id).write_text(
            json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        return rows

    rows, page_no = [], 1
    while True:
        path = config.cache_path(area_code, content_type_id, page_no)
        if path.exists() and not refresh:
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = _request_page(key, area_code, sigungu_code,
                                    content_type_id, page_no)
            # 가공하지 않은 원본 그대로 저장한다
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        items = payload if isinstance(payload, list) else _items_of(payload)
        if not items:
            break
        rows.extend(items)
        if len(items) < config.NUM_OF_ROWS:
            break
        page_no += 1
    return rows


def fetch_overviews(content_ids: list[str], refresh: bool = False) -> dict[str, str]:
    """관광지별 개요를 detailCommon2 로 받아온다. areaBasedList2 는 개요를 안 주기 때문이다."""
    config.ensure_dirs()
    path = config.RAW_DIR / "overviews.json"
    cache = {}
    if path.exists() and not refresh:
        cache = json.loads(path.read_text(encoding="utf-8"))

    key = config.get_api_key()
    todo = [str(i) for i in content_ids if str(i) not in cache]
    if key is None or not todo:
        return cache

    failed = []
    for n, cid in enumerate(todo, 1):
        try:
            res = requests.get(f"{config.API_BASE}/detailCommon2", timeout=15, params={
                "serviceKey": key, "MobileOS": "ETC", "MobileApp": "TourRec",
                "_type": "json", "contentId": cid})
            res.raise_for_status()
            items = _items_of(res.json())
            cache[cid] = (items[0].get("overview") or "").strip() if items else ""
        except Exception as exc:
            failed.append((cid, str(exc)[:60]))
            cache[cid] = ""
        if n % 50 == 0:
            print(f"  개요 수집 {n}/{len(todo)}")

    path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    # 실패를 조용히 삼키지 않는다. 몇 건이 비었는지 반드시 알린다.
    if failed:
        print(f"[경고] 개요 {len(failed)}건 수집 실패. 해당 관광지는 이름만으로 추천된다.")
        for cid, msg in failed[:3]:
            print(f"    {cid}: {msg}")
    return cache


def fetch_all(refresh: bool = False) -> list[dict]:
    """관광지·문화시설·음식점을 전부 모아 하나의 리스트로 돌려준다."""
    rows = []
    for ctype in config.CONTENT_TYPES:
        rows.extend(fetch_spots(content_type_id=ctype, refresh=refresh))
    return rows


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    data = fetch_all(refresh=refresh)
    print(f"\n총 {len(data)}건 수집")
    for ctype in config.CONTENT_TYPES:
        n = sum(1 for r in data if str(r.get("contenttypeid")) == str(ctype))
        print(f"  contentTypeId={ctype}: {n}건")
