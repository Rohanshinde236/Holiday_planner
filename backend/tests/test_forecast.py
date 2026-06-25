"""Unit tests for impact %, scoring, and combination generation."""

from engine import compute_impact_pct, score_combination, get_all_subsets, generate_combinations


def test_impact_pct():
    assert compute_impact_pct(5100, 9200) == -44.57
    assert compute_impact_pct(13200, 9800) == 34.69


def test_impact_pct_zero_baseline():
    assert compute_impact_pct(100, 0) is None


def test_all_subsets_count():
    # 3 items -> 2^3 - 1 = 7 non-empty subsets
    assert len(get_all_subsets(["Y1", "Y2", "Y3"])) == 7
    # 5 items -> 31
    assert len(get_all_subsets(["Y1", "Y2", "Y3", "Y4", "Y5"])) == 31


def test_score_in_range():
    s = score_combination("Avg(Y2+Y3)", [-44.57, -42.86], ["Y2", "Y3"], [])
    assert 0 <= s <= 100


def test_anomaly_ranks_below_clean():
    # YoY model: 3 years -> YoY points for Y1,Y2 -> combos {Y1},{Y2},{Avg(Y1+Y2)}.
    hist = {
        "Y1": {"baseline": 8500, "actual": 3600},
        "Y2": {"baseline": 9200, "actual": 5100},
        "Y3": {"baseline": 9800, "actual": 5600},
    }
    combos = generate_combinations(hist, ["Y1"], 4200)
    y1_only = next(c for c in combos if c["combo"] == "Y1")
    best = combos[0]
    # Flagging Y1 makes the clean Y2 the recommendation; Y1 ranks below but still > 0.
    assert best["combo"] == "Y2"
    assert best["score"] > y1_only["score"]
    assert y1_only["score"] > 0
