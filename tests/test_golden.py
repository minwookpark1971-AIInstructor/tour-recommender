"""골든셋 회귀 검증 - 추천 결과가 조용히 바뀌는 것을 잡는다.

test_acceptance.py 가 "기준을 만족하는가"를 본다면, 이 파일은 "어제와 같은가"를 본다.
리팩터링이 에러 없이 추천 결과만 망가뜨리는 사고를 여기서 잡는다.

기준선 파일: tests/golden/expected_recs.json

알고리즘을 **일부러** 바꿔서 기준선을 새로 잡아야 하면 아래를 실행한다.
    python tests/test_golden.py --update

주의: 테스트를 통과시키려고 --update 를 돌리지 마라. 그건 고친 게 아니라 덮은 것이다.
먼저 왜 바뀌었는지 확인하고, 의도한 변경일 때만 갱신한다.
"""
import json
from pathlib import Path

import numpy as np
import pytest

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "expected_recs.json"


def _golden() -> dict:
    """골든셋 파일을 읽는다."""
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _catalog_ids() -> set[str]:
    """지금 카탈로그에 있는 관광지 id 목록을 돌려준다."""
    from src.preprocess import load_spots
    return set(load_spots()["id"].astype(str))


def _cases(kind: str) -> list:
    """골든셋에서 해당 종류의 기준선 목록을 꺼낸다."""
    return _golden().get(kind, [])


# 시드가 하나뿐이면 그 한 곳만 안 바뀌어도 통과한다. 그래서 전부 돌린다.
CONTENT_IDS = list(range(len(_cases("content_based"))))
CF_IDS = list(range(len(_cases("collaborative"))))


def _content_case(idx: int) -> dict:
    """콘텐츠 기반 기준선 하나를 꺼낸다. 데이터가 바뀌어 seed 가 없으면 건너뛴다."""
    case = _cases("content_based")[idx]
    seed = str(case["seed_item"])
    if seed.startswith("TODO") or seed not in _catalog_ids():
        pytest.skip(f"기준선의 seed({seed})가 지금 카탈로그에 없다 - 데이터를 다시 수집한 듯하다")
    return case


def _mismatch(kind: str, expected: list, got: list) -> str:
    """무엇이 달라졌는지 사람이 읽을 수 있게 적는다."""
    return (f"{kind} 추천이 기준선과 다르다.\n"
            f"  기준선: {expected}\n"
            f"  현재  : {got}\n"
            f"  의도한 변경이면 python tests/test_golden.py --update 로 갱신하고,\n"
            f"  아니면 구현을 되돌려라.")


# ---------- 콘텐츠 기반 ----------
@pytest.mark.parametrize("idx", CONTENT_IDS)
def test_골든_콘텐츠_자기자신_제외(idx):
    from src.recommender import recommend_by_content
    case = _content_case(idx)
    recs = recommend_by_content(case["seed_item"], k=case["top_k"])
    got = [str(r["id"]) for r in recs]
    for banned in case.get("must_not_include", []):
        assert str(banned) not in got, f"{banned} 가 결과에 들어갔다"


@pytest.mark.parametrize("idx", CONTENT_IDS)
def test_골든_콘텐츠_Top5_유지(idx):
    from src.recommender import recommend_by_content
    case = _content_case(idx)
    expected = [str(i) for i in case.get("expected_top5", [])]
    if not expected:
        pytest.skip("기준선에 expected_top5 가 없다")
    got = [str(r["id"]) for r in recommend_by_content(case["seed_item"], k=case["top_k"])]
    assert got == expected, _mismatch(f"콘텐츠 기반({case['seed_title']})", expected, got)


@pytest.mark.parametrize("idx", CONTENT_IDS)
def test_골든_콘텐츠_점수_분산(idx):
    from src.recommender import recommend_by_content
    case = _content_case(idx)
    scores = [r["score"] for r in recommend_by_content(case["seed_item"], k=case["top_k"])]
    assert np.std(scores) > case.get("min_score_std", 1e-6), "유사도가 전부 같다 - 벡터화 실패 의심"
    assert all(np.isfinite(s) for s in scores), "점수에 NaN 이나 inf 가 있다"


# ---------- 협업 필터링 ----------
@pytest.mark.parametrize("idx", CF_IDS)
def test_골든_협업_방문지_제외(idx):
    from src.preprocess import get_visited
    from src.recommender import recommend_by_cf
    case = _cases("collaborative")[idx]
    if not case.get("must_exclude_visited"):
        pytest.skip("이 기준선은 방문지 제외를 요구하지 않는다")
    user = case["user_id"]
    got = {str(r["id"]) for r in recommend_by_cf(user, k=case["min_results"])}
    assert not (got & {str(v) for v in get_visited(user)}), "이미 방문한 곳을 추천했다"


@pytest.mark.parametrize("idx", CF_IDS)
def test_골든_협업_Top5_유지(idx):
    from src.recommender import recommend_by_cf
    case = _cases("collaborative")[idx]
    expected = [str(i) for i in case.get("expected_top5", [])]
    if not expected:
        pytest.skip("기준선에 expected_top5 가 없다")
    if not set(expected) <= _catalog_ids():
        pytest.skip("기준선의 추천 id 가 지금 카탈로그에 없다 - 데이터를 다시 수집한 듯하다")
    got = [str(r["id"]) for r in recommend_by_cf(case["user_id"], k=case["min_results"])]
    assert got == expected, _mismatch(f"협업 필터링({case['user_id']})", expected, got)


# ---------- 콜드스타트 ----------
def test_골든_콜드스타트_폴백():
    from src.recommender import recommend_by_cf
    case = _golden()["cold_start"][0]
    recs = recommend_by_cf(case["user_id"], k=case["min_results"])   # 예외가 나면 그대로 실패
    assert len(recs) == case["min_results"], "콜드스타트에서 개수를 못 채웠다"
    assert all(np.isfinite(r["score"]) for r in recs), "폴백 점수에 NaN 이나 inf 가 있다"


def _update() -> None:
    """지금 결과를 새 기준선으로 저장한다. 의도한 변경일 때만 쓴다."""
    from src.recommender import recommend_by_cf, recommend_by_content
    golden = _golden()

    ids = _catalog_ids()
    for case in golden.get("content_based", []):
        if str(case["seed_item"]) not in ids:
            continue
        recs = recommend_by_content(case["seed_item"], k=case["top_k"])
        case["expected_top5"] = [str(r["id"]) for r in recs]
        case["expected_top5_titles"] = [r["title"] for r in recs]
        print(f"  콘텐츠 {case.get('seed_title', case['seed_item'])}: {case['expected_top5']}")

    for cf_case in golden.get("collaborative", []):
        cf = recommend_by_cf(cf_case["user_id"], k=cf_case["min_results"])
        cf_case["expected_top5"] = [str(r["id"]) for r in cf]
        print(f"  협업 {cf_case['user_id']}: {cf_case['expected_top5']}")

    GOLDEN_PATH.write_text(json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
    print("기준선을 갱신했다.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    if "--update" in sys.argv:
        _update()
    else:
        print(__doc__)
