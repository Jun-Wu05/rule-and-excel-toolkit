from __future__ import annotations

import argparse


class ToolkitArgumentParser(argparse.ArgumentParser):
    """Shared parser with stable global options for every unified command."""


def add_common_arguments(parser: argparse.ArgumentParser, *, supports_output: bool, supports_verify: bool, supports_dry_run: bool) -> None:
    parser.add_argument("--input", required=True, help="输入文件路径")
    if supports_output:
        parser.add_argument("--output", help="输出文件路径；省略时沿用业务脚本默认命名")
    parser.add_argument("--format", choices=("human", "json"), default="human", help="输出格式")
    if supports_verify:
        parser.add_argument("--verify", action="store_true", help="执行该命令支持的验证")
    if supports_dry_run:
        parser.add_argument("--dry-run", action="store_true", help="只展示执行计划，不运行脚本或写输出")
