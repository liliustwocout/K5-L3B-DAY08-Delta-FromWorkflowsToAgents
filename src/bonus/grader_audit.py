"""Bonus B7: metamorphic relations that audit the three candidate `summarize` graders.

Each `check_*` function takes a `summarize(trials) -> dict[shape, stats]` callable and
returns a list of violations. An empty list means the relation holds. A violation is
`{"shape", "metric", "a", "b", "expected"}` so the numbers that disagree are visible.

Relations 1-3 come from `grader_audit/README.md`. Relation 4 (`permutation`) is new:
the order of the trial list must not change any statistic.
"""

from __future__ import annotations

import json
import math
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

from grader_audit import grader_a, grader_b, grader_c
from lab8.compensation import quote
from lab8.metrics import summarize as base_summarize

Summarize = Callable[[list[dict[str, Any]]], dict[str, Any]]

FIXTURES = Path(__file__).resolve().parents[1] / "grader_audit" / "fixtures"

GRADERS: dict[str, Summarize] = {
    "grader_a": grader_a.summarize,
    "grader_b": grader_b.summarize,
    "grader_c": grader_c.summarize,
}

# Ratios / means: must not change when the list is duplicated or reordered.
RATIO_KEYS = (
    "pass_rate",
    "pass_5",
    "seed_pass_rates",
    "seed_variance",
    "seed_min",
    "seed_max",
    "cost_per_success_vnd",
    "mean_steps",
    "p95_steps",
    "mean_model_calls",
    "mean_tool_calls",
)
# Totals: must double when the list is duplicated.
TOTAL_KEYS = ("trials", "graded_trials", "successes", "total_simulated_cost_vnd")
# Infra trials must not be scored as decisions of the shape.
INFRA_KEYS = (
    "graded_trials",
    "successes",
    "pass_rate",
    "pass_5",
    "seed_pass_rates",
    "seed_variance",
    "seed_min",
    "seed_max",
)


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _same(x: Any, y: Any) -> bool:
    if isinstance(x, dict) and isinstance(y, dict):
        return x.keys() == y.keys() and all(_same(x[k], y[k]) for k in x)
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return math.isclose(float(x), float(y), rel_tol=1e-9, abs_tol=1e-9)
    return x == y


def _round(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    return value


def _violation(shape: str, metric: str, a: Any, b: Any, expected: Any) -> dict[str, Any]:
    return {"shape": shape, "metric": metric, "a": _round(a), "b": _round(b), "expected": _round(expected)}


def _compare(
    summarize: Summarize,
    trials_a: list[dict[str, Any]],
    trials_b: list[dict[str, Any]],
    *,
    equal_keys: tuple[str, ...],
    double_keys: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    ra, rb = summarize(trials_a), summarize(trials_b)
    out: list[dict[str, Any]] = []
    for shape in sorted(set(ra) | set(rb)):
        sa, sb = ra.get(shape, {}), rb.get(shape, {})
        for key in equal_keys:
            if not _same(sa.get(key), sb.get(key)):
                out.append(_violation(shape, key, sa.get(key), sb.get(key), sa.get(key)))
        for key in double_keys:
            want = None if sa.get(key) is None else 2 * sa[key]
            if not _same(want, sb.get(key)):
                out.append(_violation(shape, key, sa.get(key), sb.get(key), want))
    return out


# --- Relation 1: delay_days 2 vs 3 (business decision, not via summarize) ---------

def check_claim_delay(fixture: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """2 days late is not eligible under SHIP-LATE-03 (min 3); 3 days is, for the shipping fee."""
    fx = fixture or load_fixture("metamorphic_claim_delay.json")
    order_a, order_b = fx["a"]["order"], fx["b"]["order"]
    out: list[dict[str, Any]] = []
    # The pair must differ only in delay_days, otherwise the relation says nothing.
    diff = {k for k in order_a.keys() | order_b.keys() if order_a.get(k) != order_b.get(k)}
    if diff != {"delay_days"}:
        out.append(_violation("-", "order_diff", sorted(diff), None, ["delay_days"]))
    qa = quote(order_a, fx["policies"], as_of=fx["as_of"])
    qb = quote(order_b, fx["policies"], as_of=fx["as_of"])
    if qa.amount_vnd != 0:
        out.append(_violation("-", "amount_vnd(delay=2)", qa.amount_vnd, None, 0))
    if qb.amount_vnd != int(order_b["shipping_fee_vnd"]):
        out.append(_violation("-", "amount_vnd(delay=3)", qb.amount_vnd, None, order_b["shipping_fee_vnd"]))
    if "SHIP-LATE-03" not in qb.clause_ids:
        out.append(_violation("-", "clause_ids(delay=3)", qb.clause_ids, None, ["SHIP-LATE-03"]))
    return out


# --- Relation 2: infra errors do not move the pass rate ----------------------------

def check_infra(summarize: Summarize, fixture: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    fx = fixture or load_fixture("metamorphic_infra.json")
    return _compare(summarize, fx["a"], fx["b"], equal_keys=INFRA_KEYS)


# --- Relation 3: duplicated list keeps ratios, doubles totals ----------------------

def check_duplicate(
    summarize: Summarize,
    fixture: dict[str, Any] | None = None,
    *,
    ratio_keys: tuple[str, ...] = RATIO_KEYS,
) -> list[dict[str, Any]]:
    fx = fixture or load_fixture("metamorphic_duplicate.json")
    return _compare(summarize, fx["a"], fx["b"], equal_keys=ratio_keys, double_keys=TOTAL_KEYS)


# --- Relation 4 (new): trial order must not change any statistic -------------------

def permutations(trials: list[dict[str, Any]], seed: int = 0) -> dict[str, list[dict[str, Any]]]:
    shuffled = list(trials)
    random.Random(seed).shuffle(shuffled)
    return {"reversed": list(reversed(trials)), f"shuffled_seed{seed}": shuffled}


def check_permutation(summarize: Summarize, trials: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    base = trials if trials is not None else load_fixture("metamorphic_duplicate.json")["a"]
    out: list[dict[str, Any]] = []
    keys = RATIO_KEYS + TOTAL_KEYS
    for name, perm in permutations(base).items():
        for v in _compare(summarize, base, perm, equal_keys=keys):
            out.append(dict(v, permutation=name))
    return out


# --- An order-dependent mutant: passes relations 2-3, fails relation 4 -------------

def mutant_first_seen(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Deliberately wrong grader: pass_rate from the first graded trial of each claim only.

    Mimics a real bug class ("dedupe by claim_id, keep the first row"). It is invariant
    under duplication (first rows stay first) and under appending infra trials, so the
    README relations cannot see it.
    """
    report = grader_b.summarize(trials)
    first: dict[tuple[str, str], bool] = {}
    for row in trials:
        if row.get("infra_error") or row.get("passed") is None:
            continue
        first.setdefault((row["shape"], row["claim_id"]), bool(row["passed"]))
    for shape, stats in report.items():
        picks = [ok for (sh, _), ok in first.items() if sh == shape]
        if picks:
            stats["pass_rate"] = sum(picks) / len(picks)
    return report


def audit() -> dict[str, Any]:
    """Run every relation on every grader (plus base metrics and the mutant)."""
    targets: dict[str, Summarize] = dict(GRADERS)
    targets["lab8.metrics.summarize (base)"] = base_summarize
    targets["mutant_first_seen (team-made)"] = mutant_first_seen
    no_pass5 = tuple(k for k in RATIO_KEYS if k != "pass_5")
    rows = {}
    for name, fn in targets.items():
        dup = check_duplicate(fn)
        rows[name] = {
            "infra_errors_do_not_move_pass_rate": check_infra(fn),
            "duplicated_list_keeps_rates_doubles_totals": dup,
            "duplicated_list_excluding_pass_5": check_duplicate(fn, ratio_keys=no_pass5),
            "permutation_invariance (new)": check_permutation(fn),
        }
    return {
        "delay_days_2_vs_3 (lab8.compensation.quote)": check_claim_delay(),
        "graders": rows,
    }
