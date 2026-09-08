from __future__ import annotations

import json
import re


def _unescape(raw: str) -> str:
    try:
        return json.loads(f'"{raw}"')
    except Exception:
        return raw


def extract_fields(log_str, target_fields, tail_fields=None):
    """Extract fields from JSON, quoted KV and plain KV logs.

    ``tail_fields`` marks fields whose plain ``field=value`` form consumes the
    rest of the record. This is useful for nested payload fields such as
    ``raw_data`` without hard-coding business-specific field names here.
    """
    tail_fields = set(tail_fields or ())
    result = {field: "" for field in target_fields}
    if not isinstance(log_str, str) or not log_str.strip():
        return result

    start = log_str.find("{")
    end = log_str.rfind("}") + 1
    if start != -1 and end > start:
        try:
            data = json.loads(log_str[start:end])
            infos = data.get("parsedInfos", data) if isinstance(data, dict) else None
            if isinstance(infos, dict):
                for field in target_fields:
                    value = infos.get(field, "")
                    result[field] = "" if value is None else str(value)
                return result
        except json.JSONDecodeError:
            pass

    for field in target_fields:
        escaped = re.escape(field)
        quoted = (
            re.search(rf'"{escaped}"\s*:\s*"((?:[^"\\]|\\.)*)"', log_str)
            or re.search(rf'(?<![A-Za-z0-9_]){escaped}="((?:[^"\\]|\\.)*)"', log_str)
        )
        if quoted:
            result[field] = _unescape(quoted.group(1))
            continue

        if field in tail_fields:
            plain = re.search(rf'(?<![A-Za-z0-9_]){escaped}=(.*)$', log_str, re.S)
        else:
            plain = re.search(rf'(?<![A-Za-z0-9_]){escaped}=([^;\r\n]*)', log_str)
        if plain:
            result[field] = plain.group(1).strip()

    return result
