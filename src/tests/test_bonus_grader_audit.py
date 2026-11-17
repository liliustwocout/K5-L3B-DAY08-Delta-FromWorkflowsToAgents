"""Bonus B7 — metamorphic audit of grader_audit.grader_{a,b,c}.

A grader that breaks a relation is marked `xfail(strict=True)`: the suite stays green,
the deviation is documented, and if that grader ever starts passing the relation the
test turns red (XPASS) so the table in bonus_report.md must be updated.
"""

from __future__ import annotations

import pytest

from bonus.grader_audit import (
    GRADERS,
    RATIO_KEYS,
    check_claim_delay,
    check_duplicate,
    check_infra,
    check_permutation,
    load_fixture,
    mutant_first_seen,
)
from lab8.metrics import summarize as base_summarize

NO_PASS5 = tuple(k for k in RATIO_KEYS if k != "pass_5")


def _param(name: str, *, broken: str | None = None):
    marks = [pytest.mark.xfail(strict=True, reason=broken)] if broken else []
    return pytest.param(name, marks=marks, id=name)


# --- Relation 1: delay_days 2 vs 3 -------------------------------------------------

def test_delay_2_vs_3_flips_decision_by_business_rule():
    assert check_claim_delay() == []


def test_delay_fixture_differs_only_in_delay_days():
    fx = load_fixture("metamorphic_claim_delay.json")
    a, b = fx["a"]["order"], fx["b"]["order"]
    assert (a["delay_days"], b["delay_days"]) == (2, 3)
    assert {k for k in a if a[k] != b[k]} == {"delay_days"}


# --- Relation 2: infra errors ------------------------------------------------------

def test_infra_fixture_b_is_a_plus_infra_rows():
    fx = load_fixture("metamorphic_infra.json")
    extra = fx["b"][len(fx["a"]):]
    assert fx["b"][: len(fx["a"])] == fx["a"]
    assert extra and all(row["infra_error"] for row in extra)


@pytest.mark.parametrize(
    "name",
    [
        _param("grader_a"),
        _param("grader_b"),
        _param("grader_c", broken="counts infra_error trials as failed decisions (pass_rate 0.75 -> 0.5625)"),
    ],
)
def test_infra_errors_do_not_move_pass_rate(name):
    assert check_infra(GRADERS[name]) == []


# --- Relation 3: duplicated list (pass_5 checked separately) -----------------------

@pytest.mark.parametrize(
    "name",
    [
        _param("grader_a", broken="adds the first trial cost of each claim a second time (total 189.5 -> 283.5)"),
        _param("grader_b"),
        _param("grader_c"),
    ],
)
def test_duplicate_keeps_rates_and_doubles_totals(name):
    assert check_duplicate(GRADERS[name], ratio_keys=NO_PASS5) == []


@pytest.mark.parametrize(
    "fn",
    [
        pytest.param(base_summarize, id="lab8.metrics"),
        *[pytest.param(GRADERS[n], id=n) for n in ("grader_a", "grader_b", "grader_c")],
    ],
)
@pytest.mark.xfail(
    strict=True,
    reason="lab8.metrics.summarize: pass^5 requires len(rows of claim) == len(seeds), so a duplicated list drops pass_5 0.667 -> 0",
)
def test_duplicate_keeps_pass5(fn):
    assert [v for v in check_duplicate(fn) if v["metric"] == "pass_5"] == []


# --- Relation 4 (new): permutation invariance --------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        _param("grader_a", broken="the extra cost depends on which trial of a claim is seen first"),
        _param("grader_b"),
        _param("grader_c"),
    ],
)
def test_trial_order_does_not_change_statistics(name):
    assert check_permutation(GRADERS[name]) == []


def test_new_relation_catches_bug_the_readme_relations_miss():
    """mutant_first_seen passes infra + duplicate, yet the permutation relation exposes it."""
    assert check_infra(mutant_first_seen) == []
    assert check_duplicate(mutant_first_seen, ratio_keys=NO_PASS5) == []
    violations = check_permutation(mutant_first_seen)
    assert any(v["metric"] == "pass_rate" for v in violations)
