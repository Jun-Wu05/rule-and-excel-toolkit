#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import exit_codes
from common.output import emit_result
from common.registry import CommandSpec, get_command, iter_commands
from common.result import CommandResult, VerificationResult


def _dest(flag: str) -> str:
    return flag.lstrip("-").replace("-", "_")


def _default_output(input_path: str, suffix: str | None) -> str | None:
    if not suffix:
        return None
    base, ext = os.path.splitext(input_path)
    return f"{base}{suffix}{ext}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toolkit.py", description="rule-and-excel-toolkit unified CLI")
    domains = parser.add_subparsers(dest="domain")
    for domain in ("rule", "excel"):
        dp = domains.add_parser(domain, help=f"{domain} commands")
        commands = dp.add_subparsers(dest="command")
        for spec in iter_commands(domain):
            cp = commands.add_parser(spec.name, aliases=list(spec.aliases), help=spec.description, description=spec.description)
            cp.set_defaults(_spec=spec)
            cp.add_argument("--input", required=True, help="输入文件路径")
            if spec.supports_output:
                cp.add_argument("--output", help="输出文件路径；省略时使用统一默认命名")
            cp.add_argument("--format", choices=("human", "json"), default="human")
            if spec.supports_verify:
                cp.add_argument("--verify", action="store_true")
            if spec.supports_dry_run:
                cp.add_argument("--dry-run", action="store_true")
            for opt in spec.options:
                cp.add_argument(opt.flag, **dict(opt.kwargs))
    return parser


def build_legacy_argv(spec: CommandSpec, args: argparse.Namespace, output_path: str | None) -> list[str]:
    cmd = [sys.executable, str(SCRIPT_DIR / spec.script)]
    if spec.command_id == "excel.join":
        cmd.append(args.input)
        cmd.append(output_path or "")
        cmd.extend(args.log_files)
    else:
        cmd.append(args.input)
        if spec.supports_output:
            cmd.append(output_path or "")

    for opt in spec.options:
        dest = _dest(opt.flag)
        value = getattr(args, dest, None)
        if spec.command_id == "excel.join" and opt.flag == "--log-files":
            continue
        legacy_flag = opt.legacy_flag or opt.flag
        action = opt.kwargs.get("action")
        if action == "store_true":
            if value:
                cmd.append(legacy_flag)
        elif value is not None:
            cmd.extend([legacy_flag, str(value)])

    if getattr(args, "verify", False):
        if spec.command_id == "rule.reuuid":
            cmd.append("--verify")
        elif spec.command_id == "excel.extract" and getattr(args, "verify_sample", 0) <= 0:
            cmd.extend(["--verify-sample", "20"])
    return cmd


def infer_verification(spec: CommandSpec, args: argparse.Namespace, stdout: str, returncode: int) -> VerificationResult:
    if returncode != 0:
        return VerificationResult(status="fail", details={"returncode": returncode})
    if spec.command_id == "rule.clone-entry":
        if "全部通过" in stdout:
            return VerificationResult(status="pass", details={"source": "intrinsic"})
        if "有异常" in stdout:
            return VerificationResult(status="fail", details={"source": "intrinsic"})
    if spec.command_id == "excel.extract" and (getattr(args, "verify", False) or getattr(args, "verify_sample", 0) > 0):
        if "抽查存在不一致" in stdout or "不一致的" in stdout:
            return VerificationResult(status="fail", details={"source": "verify-sample"})
        if "抽查回对" in stdout:
            return VerificationResult(status="pass", details={"source": "verify-sample"})
    if getattr(args, "verify", False):
        return VerificationResult(status="pass", details={"source": "legacy-command", "returncode": 0})
    return VerificationResult(status="not_run")


def run_command(spec: CommandSpec, args: argparse.Namespace) -> tuple[CommandResult, int]:
    output_path = getattr(args, "output", None) if spec.supports_output else None
    if spec.supports_output and not output_path:
        output_path = _default_output(args.input, spec.output_suffix)
    argv = build_legacy_argv(spec, args, output_path)

    if getattr(args, "dry_run", False):
        return CommandResult(
            status="success",
            command=spec.command_id,
            input=args.input,
            output=output_path,
            stats={"dry_run": True, "legacy_argv": argv},
        ), exit_codes.SUCCESS

    try:
        completed = subprocess.run(argv, text=True, capture_output=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        return CommandResult(status="error", command=spec.command_id, input=args.input, output=output_path, error=str(exc)), exit_codes.EXECUTION_ERROR

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    verification = infer_verification(spec, args, stdout + "\n" + stderr, completed.returncode)
    warnings = []
    for line in stdout.splitlines():
        if "[WARN]" in line or "⚠" in line:
            warnings.append(line.strip())

    status = "success" if completed.returncode == 0 and verification.status != "fail" else "error"
    error = None if status == "success" else (stderr.strip() or "legacy command failed or verification did not pass")
    result = CommandResult(
        status=status,
        command=spec.command_id,
        input=args.input,
        output=output_path,
        stats={"returncode": completed.returncode},
        verification=verification,
        warnings=warnings,
        error=error,
        legacy_stdout=stdout.strip() or None,
    )
    if completed.returncode != 0:
        return result, exit_codes.EXECUTION_ERROR
    if verification.status == "fail":
        return result, exit_codes.VERIFY_FAILED
    return result, exit_codes.SUCCESS


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "domain", None):
        parser.print_help()
        return exit_codes.SUCCESS
    if not getattr(args, "command", None):
        parser.parse_args([args.domain, "--help"])
    spec = getattr(args, "_spec", None) or get_command(args.domain, args.command)
    if spec is None:
        parser.error("unknown command")
    result, code = run_command(spec, args)
    emit_result(result, args.format)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
