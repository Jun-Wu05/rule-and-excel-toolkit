from __future__ import annotations

import json
import sys
from .result import CommandResult


def emit_result(result: CommandResult, fmt: str = "human") -> None:
    if fmt == "json":
        json.dump(result.to_dict(), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

    print(f"[INFO] command={result.command}")
    if result.input is not None:
        print(f"[INFO] input={result.input}")
    for key, value in result.stats.items():
        print(f"[STATS] {key}={value}")
    for warning in result.warnings:
        print(f"[WARN] {warning}")
    print(f"[VERIFY] status={result.verification.status}")
    for key, value in result.verification.details.items():
        print(f"[VERIFY] {key}={value}")
    if result.output:
        print(f"[OUTPUT] path={result.output}")
    if result.error:
        print(f"[ERROR] {result.error}")
