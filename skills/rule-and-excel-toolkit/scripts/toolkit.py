#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common.registry import iter_commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toolkit.py",
        description="rule-and-excel-toolkit unified CLI",
    )
    sub = parser.add_subparsers(dest="domain")
    for domain in ("rule", "excel"):
        domain_parser = sub.add_parser(domain, help=f"{domain} commands")
        domain_sub = domain_parser.add_subparsers(dest="command")
        for spec in iter_commands(domain):
            domain_sub.add_parser(spec.name, help=spec.description)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.domain:
        parser.print_help()
        return 0
    if not args.command:
        parser.parse_args([args.domain, "--help"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
