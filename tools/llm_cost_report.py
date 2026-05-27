"""
LLM cost report — reads llm_calls.jsonl and prints a per-agent breakdown.

Usage:
    python tools/llm_cost_report.py
    python tools/llm_cost_report.py path/to/llm_calls.jsonl

Cost table ($/1k tokens) can be overridden via environment variables:
    LLM_COST_INPUT   — cost per 1k prompt tokens    (default: 0.0025 for gpt-4o)
    LLM_COST_OUTPUT  — cost per 1k completion tokens (default: 0.0100 for gpt-4o)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

_DEFAULT_COST_INPUT  = 0.0025   # $/1k prompt tokens (gpt-4o)
_DEFAULT_COST_OUTPUT = 0.0100   # $/1k completion tokens (gpt-4o)


def _default_log_path() -> Path:
    try:
        from platformdirs import user_data_path
        return user_data_path("DungeonDaddy", appauthor=False) / "llm_calls.jsonl"
    except Exception:
        return Path.home() / ".dungeon_daddy" / "llm_calls.jsonl"


def read_records(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    records = []
    for i, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"  WARNING: skipping malformed line {i}", file=sys.stderr)
    return records


def summarise(records: list[dict], cost_input: float, cost_output: float) -> None:
    if not records:
        print("No records found.")
        return

    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "duration_ms": 0.0}
    )

    for r in records:
        agent = r.get("agent", "unknown")
        totals[agent]["calls"]             += 1
        totals[agent]["prompt_tokens"]     += r.get("prompt_tokens", 0)
        totals[agent]["completion_tokens"] += r.get("completion_tokens", 0)
        totals[agent]["duration_ms"]       += r.get("duration_ms", 0.0)

    print(f"\n{'Agent':<12} {'Calls':>6} {'Prompt':>10} {'Completion':>12} {'Duration':>10} {'Cost':>10}")
    print("-" * 64)

    grand_calls = grand_prompt = grand_completion = grand_dur = grand_cost = 0.0
    for agent, t in sorted(totals.items()):
        cost = (t["prompt_tokens"] / 1000 * cost_input) + (t["completion_tokens"] / 1000 * cost_output)
        print(
            f"{agent:<12} {t['calls']:>6} {t['prompt_tokens']:>10,} "
            f"{t['completion_tokens']:>12,} {t['duration_ms']/1000:>9.1f}s "
            f"  ${cost:>7.4f}"
        )
        grand_calls      += t["calls"]
        grand_prompt     += t["prompt_tokens"]
        grand_completion += t["completion_tokens"]
        grand_dur        += t["duration_ms"]
        grand_cost       += cost

    print("-" * 64)
    print(
        f"{'TOTAL':<12} {int(grand_calls):>6} {int(grand_prompt):>10,} "
        f"{int(grand_completion):>12,} {grand_dur/1000:>9.1f}s "
        f"  ${grand_cost:>7.4f}"
    )
    print(f"\n{len(records)} call(s) total. Cost table: ${cost_input:.4f}/1k input, ${cost_output:.4f}/1k output.\n")


def main() -> None:
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _default_log_path()
    cost_input  = float(os.environ.get("LLM_COST_INPUT",  _DEFAULT_COST_INPUT))
    cost_output = float(os.environ.get("LLM_COST_OUTPUT", _DEFAULT_COST_OUTPUT))

    print(f"Reading: {log_path}")
    records = read_records(log_path)
    summarise(records, cost_input, cost_output)


if __name__ == "__main__":
    main()
