from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class OptionSpec:
    flag: str
    legacy_flag: str | None = None
    kwargs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CommandSpec:
    domain: str
    name: str
    script: str
    description: str
    supports_output: bool = True
    supports_verify: bool = False
    supports_dry_run: bool = True
    aliases: Sequence[str] = field(default_factory=tuple)
    output_suffix: str | None = None
    options: Sequence[OptionSpec] = field(default_factory=tuple)

    @property
    def command_id(self) -> str:
        return f"{self.domain}.{self.name}"


O = OptionSpec
COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec("rule", "hierarchy", "rule_hierarchy_number.py", "按 ref 生成层级编号", supports_verify=True, output_suffix="_层级编号", options=(O("--prefix", kwargs={"default": None}),)),
    CommandSpec("rule", "clear-field", "rule_clear_field.py", "置空/删除 normalize.field", supports_verify=True, output_suffix="_字段处理", options=(O("--fields", kwargs={"required": True}), O("--mode", kwargs={"choices": ("clear", "remove"), "default": "clear"}))),
    CommandSpec("rule", "reuuid", "rule_replace_uuid.py", "替换顶层 UUID 并同步引用", supports_verify=True, output_suffix="_reuuid", options=(O("--prefix", kwargs={"default": ""}), O("--suffix", kwargs={"default": ""}), O("--prefix-only", kwargs={"action": "store_true"}))),
    CommandSpec("rule", "clone-entry", "rule_clone_entry.py", "只克隆入口规则", supports_verify=True, output_suffix="_入口复制", options=(O("--suffixes", kwargs={"default": "_new1,_new2"}),)),
    CommandSpec("rule", "link", "rule_link_conditionmatch.py", "组装 conditionMatch 规则链", supports_verify=True, output_suffix="_规则链"),
    CommandSpec("excel", "inspect", "excel_inspect.py", "预检日志格式与字段分布", supports_output=False, options=(O("--log-column", kwargs={"default": "原始日志"}), O("--fields", kwargs={"default": "node_ip,node_name,log_msg"}), O("--sample", kwargs={"type": int, "default": 200}))),
    CommandSpec("excel", "extract", "excel_extract_log_fields.py", "从日志列提取字段", supports_verify=True, output_suffix="_提取", options=(O("--log-column", kwargs={"default": "原始日志"}), O("--fields"), O("--no-diag", kwargs={"action": "store_true"}), O("--verify-sample", kwargs={"type": int, "default": 0}))),
    CommandSpec("excel", "filter", "excel_filter_logs.py", "按关键词筛选日志", supports_verify=True, output_suffix="_筛选", options=(O("--keyword", kwargs={"default": "alarmExtendFieldsStrategyName"}), O("--column", kwargs={"default": "原始日志"}))),
    CommandSpec("excel", "split", "excel_split_by_deviceaddress.py", "按字段值拆分多 Sheet", supports_verify=True, output_suffix="_拆分", options=(O("--log-column", kwargs={"default": "原始日志"}), O("--fields", kwargs={"default": "deviceName,productVendorName,deviceSendProductName,dvcAddress,rawEvent,deviceAddress,dataType"}), O("--split-field", kwargs={"default": "deviceAddress"}), O("--keep-columns"), O("--keep-all-columns", kwargs={"action": "store_true"}), O("--tail-fields", kwargs={"default": "raw_data"}), O("--no-full-sheet", kwargs={"action": "store_true"}))),
    CommandSpec("excel", "dedup", "excel_dedup_sheets.py", "按指定列分别去重", supports_verify=True, output_suffix="_去重", options=(O("--log-column", kwargs={"default": "原始日志"}), O("--fields", kwargs={"default": "log_msg"}), O("--dedup-cols", kwargs={"required": True}))),
    CommandSpec("excel", "join", "excel_device_log_join.py", "设备清单与日志按 IP 关联", supports_verify=True, output_suffix="_关联", options=(O("--log-files", kwargs={"nargs": "+", "required": True}), O("--device-ip-col", kwargs={"default": "设备IP"}), O("--device-name-col", kwargs={"default": "设备名称"}), O("--device-vendor-col", kwargs={"default": "设备厂商"}), O("--log-ip-col", kwargs={"default": "设备描述"}), O("--log-keep-col", kwargs={"default": "原始保留"}), O("--log-column", legacy_flag="--log-col", kwargs={"default": "原始日志"}))),
)


def iter_commands(domain: str | None = None):
    for spec in COMMANDS:
        if domain is None or spec.domain == domain:
            yield spec


def get_command(domain: str, name: str) -> CommandSpec | None:
    for spec in COMMANDS:
        if spec.domain == domain and (spec.name == name or name in spec.aliases):
            return spec
    return None
