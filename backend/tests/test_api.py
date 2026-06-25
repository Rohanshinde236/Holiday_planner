"""
API smoke tests — the FastAPI layer delegates to the engine and validates input.
"""

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_shrinkage_endpoint():
    r = client.post("/api/shrinkage", json={"planned_leave_pct": 8, "unplanned_leave_pct": 5, "training_pct": 3})
    assert r.status_code == 200
    assert r.json()["total_shrinkage_pct"] == 15.22


def test_erlang_endpoint_matches_engine():
    r = client.post("/api/erlang_c", json={"calls_per_hour": 384.1, "aht_seconds": 360,
                                           "sl_target_pct": 80, "sl_target_seconds": 20,
                                           "total_shrinkage_pct": 15.22})
    body = r.json()
    assert body["net_hc"] == 48
    assert body["gross_hc"] == 57


def test_combinations_endpoint():
    r = client.post("/api/combinations", json={
        "historical": {"Y1": {"actual": 3600, "baseline": 8500},
                       "Y2": {"actual": 5100, "baseline": 9200},
                       "Y3": {"actual": 5600, "baseline": 9800}},
        "anomaly_years": ["Y1"], "plan_volume": 4200,
    })
    combos = r.json()["combinations"]
    # YoY model + Y1 flagged -> Y2 is the recommended combo (3 combos total)
    assert combos[0]["combo"] == "Y2"
    assert len(combos) == 3


def test_validation_rejects_bad_aht():
    # AHT must be > 0 — Pydantic should reject with 422 before any math runs
    r = client.post("/api/erlang_c", json={"calls_per_hour": 100, "aht_seconds": 0})
    assert r.status_code == 422


def test_shift_optimise_ilp_endpoint():
    reqs = [{"interval": i + 1, "start": f"{8 + i}:00", "net_hc": v}
            for i, v in enumerate([5, 8, 6, 3])]
    shifts = [{"name": "A", "start": "08:00", "end": "10:00"},
              {"name": "B", "start": "10:00", "end": "12:00"}]
    r = client.post("/api/shift_optimise", json={
        "hc_requirements": reqs, "available_shifts": shifts,
        "operating_start": "08:00", "operating_end": "12:00",
        "mode": "ilp", "available_agents": 100,
    })
    body = r.json()
    assert body["mode"] == "ilp"
    assert body["intervals_at_risk"] == 0
