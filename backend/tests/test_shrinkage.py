"""Unit tests for compound shrinkage and net->gross."""

import math
from engine import compound_shrinkage, gross_hc, gross_hc_ceil, GROSS_SENTINEL


def test_compound_not_additive():
    r = compound_shrinkage(8, 5, 3)
    # compound (15.22%) must be LESS than naive sum (16%)
    assert r["total_shrinkage_pct"] == 15.22
    assert r["total_shrinkage_pct"] < 16.0


def test_gross_multiplier():
    r = compound_shrinkage(8, 5, 3)
    assert r["gross_multiplier"] == 1.1796


def test_gross_hc_inflates():
    assert math.ceil(gross_hc(48, 15.22)) == 57


def test_gross_hc_zero_shrinkage():
    assert gross_hc(50, 0) == 50.0


def test_gross_hc_full_shrinkage_is_inf():
    assert gross_hc(10, 100) == float("inf")


def test_gross_hc_ceil_normal():
    assert gross_hc_ceil(48, 15.22) == 57


def test_gross_hc_ceil_full_shrinkage_no_crash():
    # 100% shrinkage must NOT crash (was math.ceil(inf) -> OverflowError); returns sentinel
    assert gross_hc_ceil(10, 100) == GROSS_SENTINEL
