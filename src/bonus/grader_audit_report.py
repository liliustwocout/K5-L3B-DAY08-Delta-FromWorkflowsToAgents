"""Write reports/bonus_grader_audit.json from a fresh run of every relation.

Run in src/:  python -m bonus.grader_audit_report --out reports/bonus_grader_audit.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bonus.grader_audit import audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="reports/bonus_grader_audit.json")
    args = parser.parse_args()

    result = audit()
    table = {
        grader: {rel: ("ok" if not v else f"violated x{len(v)}") for rel, v in rels.items()}
        for grader, rels in result["graders"].items()
    }
    delay = result["delay_days_2_vs_3 (lab8.compensation.quote)"]
    body = {
        "topic": "B7 grader audit",
        "command": "python -m bonus.grader_audit_report --out reports/bonus_grader_audit.json",
        "delay_days_2_vs_3": "ok" if not delay else delay,
        "table": table,
        "details": result["graders"],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    short = ["infra", "duplicate", "dup_no_pass5", "permutation"]
    width = max(len(g) for g in table)
    print(f"delay_days_2_vs_3: {'ok' if not delay else 'VIOLATED'}")
    print(f"{'':<{width}}  " + "".join(f"{s:<16}" for s in short))
    for grader, cells in table.items():
        print(f"{grader:<{width}}  " + "".join(f"{c:<16}" for c in cells.values()))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
