from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


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

    @property
    def command_id(self) -> str:
        return f"{self.domain}.{self.name}"


COMMANDS: tuple[CommandSpec, ...] = ()


def iter_commands(domain: str | None = None):
    for spec in COMMANDS:
        if domain is None or spec.domain == domain:
            yield spec


def get_command(domain: str, name: str) -> CommandSpec | None:
    for spec in COMMANDS:
        if spec.domain != domain:
            continue
        if spec.name == name or name in spec.aliases:
            return spec
    return None
