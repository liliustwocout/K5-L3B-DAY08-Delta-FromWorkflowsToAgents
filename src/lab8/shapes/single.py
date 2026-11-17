"""Shape B — one ReAct agent. Student work.

Use `lab8.runtime.run_react` with max_steps=8. `decide` calls `MockLLM.complete`
inside the loop to select among read-only tools. It must not call `issue_refund`.
After the loop, the host validates the quote and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import ToolRejected, run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import get_claim_view, tool_cost
from lab8.trace import Trace

_CLAUSE_RE = re.compile(r"\b([A-Z]+-[A-Z]+-[A-Z0-9]+)\b")


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Run one claim through the bounded single ReAct agent shape."""
    return _run_with_mode(
        claim_id,
        seed=seed,
        store_path=store_path,
        crash_at=crash_at,
        shape="single",
        use_llm=True,
    )


def run_claim_no_llm(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    """Ablation variant: identical bounded ReAct loop with deterministic tool selector (0 model calls)."""
    return _run_with_mode(
        claim_id,
        seed=seed,
        store_path=store_path,
        crash_at=crash_at,
        shape="single_no_llm",
        use_llm=False,
    )


def _run_with_mode(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None,
    shape: str,
    use_llm: bool,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(
            conn,
            claim_id,
            seed=seed,
            crash_at=crash_at,
            shape=shape,
            use_llm=use_llm,
        )
    finally:
        conn.close()


def _cited_clause(ticket: str) -> str | None:
    match = _CLAUSE_RE.search(ticket or "")
    return match.group(1) if match else None


def _parse_parsed_delay(text: str) -> int | None:
    match = re.search(r"parsed_delay=(\d+)", text)
    return int(match.group(1)) if match else None


def _parse_directive(thought: str) -> tuple[str, str] | None:
    """Support explicit tool=/final= directives when driven by an LLM or test double."""
    tool_match = re.search(r"\btool=([a-zA-Z0-9_]+)\b", thought)
    if tool_match:
        return ("tool", tool_match.group(1))
    final_match = re.search(r"\bfinal=([a-zA-Z0-9_]+)\b", thought)
    if final_match:
        return ("final", final_match.group(1))
    return None


def _digest_index(thought: str, count: int) -> int:
    tail = thought.rsplit(":", 1)[-1].strip()
    try:
        return int(tail, 16) % count
    except ValueError:
        return 0


def _default_args_for_tool(tool_name: str, claim_view: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "get_claim_view":
        return {"claim_id": claim_view["claim_id"]}
    if tool_name in ("lookup_order", "lookup_refund_history"):
        return {
            "order_id": claim_view.get("order_id"),
            "principal_id": claim_view.get("principal_id"),
        }
    if tool_name == "get_clause":
        return {"clause_id": state["cited_clause"] or "SHIP-LATE-03"}
    if tool_name == "compute_compensation":
        order_view = state.get("order_view") or {}
        return {"order": order_view.get("order") or {}}
    return {}


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
    shape: str,
    use_llm: bool,
) -> RunResult:
    budget = Budget()
    run_id = make_run_id(shape, claim_id, seed)
    trace = Trace(run_id)

    budget.add_tool(tool_cost())
    claim_view = get_claim_view(conn, claim_id)
    trace.add(
        "claim_loaded",
        {
            "found": bool(claim_view.get("found")),
            "claim_id": claim_id,
            "has_order_id": bool(claim_view.get("order_id")),
        },
    )
    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    state: dict[str, Any] = {
        "parsed": False,
        "parsed_delay": None,
        "cited_clause": _cited_clause(str(claim_view.get("ticket") or "")),
        "order_view": None,
        "policy_loaded": False,
        "policy_count": 0,
        "refund_history": None,
        "checked_clause": None,
        "quote": None,
        "steps": 0,
    }

    def _obs_prompt(candidates: list[str]) -> str:
        order_info = (state["order_view"] or {}).get("order") or {}
        return (
            f"step={state['steps']}|has_order={bool(claim_view.get('order_id'))}"
            f"|order_loaded={state['order_view'] is not None}"
            f"|order_delay={order_info.get('delay_days')}"
            f"|parsed_delay={state['parsed_delay']}"
            f"|policy={state['policy_loaded']}"
            f"|history={state['refund_history'] is not None}"
            f"|clause={state['checked_clause'] is not None}"
            f"|quoted={state['quote'] is not None}"
            f"|candidates={','.join(candidates)}"
        )

    def _record_observation(last_tool: str | None, last_result: Any, step: int) -> None:
        if last_tool is None:
            return
        if last_tool == "lookup_order":
            order_view = last_result if isinstance(last_result, dict) else {}
            state["order_view"] = order_view
            trace.add(
                "react_observation",
                {
                    "step": step,
                    "tool": "lookup_order",
                    "visible": bool(order_view.get("visible")),
                    "reason": order_view.get("reason"),
                },
            )
        elif last_tool == "lookup_policy":
            policies = (last_result or {}).get("policies") if isinstance(last_result, dict) else []
            state["policy_loaded"] = True
            state["policy_count"] = len(policies or [])
            trace.add(
                "react_observation",
                {"step": step, "tool": "lookup_policy", "policy_count": state["policy_count"]},
            )
        elif last_tool == "lookup_refund_history":
            hist = last_result if isinstance(last_result, dict) else {}
            state["refund_history"] = hist
            trace.add(
                "react_observation",
                {
                    "step": step,
                    "tool": "lookup_refund_history",
                    "refunded_vnd": int(hist.get("refunded_vnd") or 0),
                    "refund_count": int(hist.get("refund_count") or 0),
                },
            )
        elif last_tool == "get_clause":
            clause_res = last_result if isinstance(last_result, dict) else {}
            state["checked_clause"] = clause_res
            trace.add(
                "react_observation",
                {
                    "step": step,
                    "tool": "get_clause",
                    "found": bool(clause_res.get("found")),
                    "is_current": clause_res.get("is_current"),
                },
            )
        elif last_tool == "compute_compensation":
            quote_payload = last_result if isinstance(last_result, dict) else {}
            state["quote"] = quote_payload
            trace.add("quote", safe_dump(quote_payload))

    def _candidate_tools() -> list[str]:
        if not claim_view.get("order_id"):
            return []
        if state["order_view"] is None:
            return ["lookup_order"]
        if not state["order_view"].get("visible"):
            return []
        if state["quote"] is not None:
            return []
        candidates: list[str] = []
        if not state["policy_loaded"]:
            candidates.append("lookup_policy")
        if state["refund_history"] is None:
            candidates.append("lookup_refund_history")
        if state["checked_clause"] is None and state["cited_clause"] is not None:
            candidates.append("get_clause")
        if not candidates:
            candidates.append("compute_compensation")
        return candidates

    def decide(obs: dict[str, Any]) -> dict[str, Any]:
        state["steps"] += 1
        step = state["steps"]
        _record_observation(obs.get("last_tool"), obs.get("last_result"), step)

        if use_llm and not state["parsed"]:
            parse_text = complete(budget, seed=seed, purpose="parse", prompt=str(claim_view.get("ticket") or ""))
            state["parsed"] = True
            state["parsed_delay"] = _parse_parsed_delay(parse_text)
            trace.add("react_thought", {"step": step, "purpose": "parse", "output": parse_text})

        candidates = _candidate_tools()
        thought = ""
        if use_llm:
            thought = complete(budget, seed=seed, purpose="react_step", prompt=_obs_prompt(candidates))
            directive = _parse_directive(thought)
            if directive is not None:
                kind, target = directive
                if kind == "tool":
                    trace.add("react_action", {"step": step, "tool": target, "source": "model_directive"})
                    return {"tool": target, "args": _default_args_for_tool(target, claim_view, state)}
                trace.add("react_decision", {"step": step, "status": target, "source": "model_directive"})
                return {"final": {"status": target, "error_reason": "model_final"}}

        if not claim_view.get("order_id"):
            if use_llm:
                complete(budget, seed=seed, purpose="draft", prompt="needs_info")
            trace.add("react_decision", {"step": step, "status": "needs_info", "reason": "missing_order_id"})
            return {"final": {"status": "needs_info", "error_reason": "missing_order_id"}}

        if state["order_view"] is not None and not state["order_view"].get("visible"):
            reason = str(state["order_view"].get("reason") or "outside_principal_scope")
            if use_llm:
                complete(budget, seed=seed, purpose="draft", prompt="escalated")
            trace.add("react_decision", {"step": step, "status": "escalated", "reason": reason})
            return {"final": {"status": "escalated", "error_reason": reason}}

        if state["quote"] is not None:
            proposal = int(state["quote"].get("amount_vnd") or 0)
            if use_llm:
                complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")
            return {
                "final": {
                    "status": "quoted",
                    "proposal_amount": proposal,
                    "reason": state["quote"].get("reason"),
                }
            }

        idx = _digest_index(thought, len(candidates)) if use_llm else 0
        chosen = candidates[idx]
        trace.add(
            "react_action",
            {
                "step": step,
                "tool": chosen,
                "candidates": candidates,
                "selector": "mock_llm" if use_llm else "deterministic",
            },
        )
        return {"tool": chosen, "args": _default_args_for_tool(chosen, claim_view, state)}

    try:
        react_out = run_react(
            conn,
            budget,
            observation={"claim": claim_view},
            decide=decide,
            max_steps=8,
            worker=True,
        )
    except ToolRejected as exc:
        trace.add("error", {"reason": "tool_rejected", "detail": str(exc)})
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="tool_rejected",
        )

    if react_out.get("stopped") == "step_cap":
        trace.add("error", {"reason": "step_cap"})
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="step_cap",
        )

    final = react_out.get("final") or {}
    final_status = final.get("status")
    if final_status in ("needs_info", "escalated"):
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status=str(final_status),
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("error_reason"),
        )

    if final_status != "quoted" or state["quote"] is None:
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("error_reason") or "invalid_react_final",
        )

    quote_payload = state["quote"]
    proposal = int(quote_payload.get("amount_vnd") or 0)
    if proposal <= 0:
        trace.add(
            "decision",
            {"status": "denied", "proposal_amount": 0, "reason": quote_payload.get("reason")},
        )
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=quote_payload.get("reason"),
        )

    try:
        # Pass the FULL quote; the host validates approval and subtracts prior order refunds.
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    trace.add(
        "host_outcome",
        {
            "ok": bool(outcome["ok"]),
            "reason": outcome["reason"],
            "conflict": bool(outcome["conflict"]),
        },
    )
    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        return finish(
            conn,
            shape=shape,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )

    return finish(
        conn,
        shape=shape,
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )
