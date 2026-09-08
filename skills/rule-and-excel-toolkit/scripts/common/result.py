from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0"


@dataclass
class VerificationResult:
    status: str = "not_run"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandResult:
    status: str
    command: str
    input: Any = None
    output: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    verification: VerificationResult = field(default_factory=VerificationResult)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    legacy_stdout: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        return data
