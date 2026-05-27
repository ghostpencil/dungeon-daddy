"""Run AI output evals and write or compare baseline_scores.json.

Usage:
    python tools/run_evals.py          # run evals, save baseline if none exists
    python tools/run_evals.py --update # overwrite baseline with current scores
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_BASELINE = Path("tests/evals/baseline_scores.json")
_RESULT_RE = re.compile(
    r"(tests[/\\]evals[/\\]\S+::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR)"
)


def _run_pytest() -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/evals/", "-m", "eval", "-v", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def _parse_results(output: str) -> list[dict[str, str]]:
    tests = []
    for line in output.splitlines():
        m = _RESULT_RE.search(line)
        if m:
            tests.append({"test": m.group(1).replace("\\", "/"), "result": m.group(2)})
    return tests


def main(update: bool = False) -> int:
    print("[run_evals] Running eval suite…")
    exit_code, output = _run_pytest()

    tests = _parse_results(output)
    summary = {
        "passed": sum(1 for t in tests if t["result"] == "PASSED"),
        "failed": sum(1 for t in tests if t["result"] == "FAILED"),
        "skipped": sum(1 for t in tests if t["result"] == "SKIPPED"),
        "error": sum(1 for t in tests if t["result"] == "ERROR"),
    }
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "exit_code": exit_code,
        "summary": summary,
        "tests": tests,
    }

    print(output)

    if not _BASELINE.exists() or update:
        _BASELINE.write_text(json.dumps(report, indent=2))
        label = "updated" if _BASELINE.exists() and update else "saved"
        print(f"[run_evals] Baseline {label}: {_BASELINE}")
    else:
        baseline = json.loads(_BASELINE.read_text())
        prev = baseline.get("summary", {}).get("passed", 0)
        curr = summary["passed"]
        total = len(tests)
        if curr < prev:
            print(f"[run_evals] REGRESSION: {prev} → {curr} passing ({total} total)")
            exit_code = max(exit_code, 1)
        else:
            print(f"[run_evals] OK: {curr}/{total} passing (baseline: {prev})")

    return exit_code


if __name__ == "__main__":
    update_flag = "--update" in sys.argv
    sys.exit(main(update=update_flag))
