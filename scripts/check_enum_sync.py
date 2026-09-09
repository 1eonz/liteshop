"""校验共享 TypeScript 枚举与后端 StrEnum 的值保持一致。"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ENUM_PATTERN = re.compile(r"export enum (?P<name>\w+)\s*\{(?P<body>[^}]*)\}", re.DOTALL)
VALUE_PATTERN = re.compile(r"^\s*(?P<name>\w+)\s*=\s*'(?P<value>[^']+)'\s*,?\s*$")
PY_ENUM_PATTERN = re.compile(r"class (?P<name>\w+)\(StrEnum\):(?P<body>.*?)(?=\n\nclass |\Z)", re.DOTALL)
PY_VALUE_PATTERN = re.compile(r"^\s*(?P<name>\w+)\s*=\s*\"(?P<value>[^\"]+)\"\s*$")


def parse_typescript(path: Path) -> dict[str, dict[str, str]]:
    enums: dict[str, dict[str, str]] = {}
    for match in ENUM_PATTERN.finditer(path.read_text(encoding="utf-8")):
        values: dict[str, str] = {}
        for line in match.group("body").splitlines():
            value = VALUE_PATTERN.match(line)
            if value:
                values[value.group("name")] = value.group("value")
        enums[match.group("name")] = values
    return enums


def parse_python(paths: list[Path]) -> dict[str, dict[str, str]]:
    enums: dict[str, dict[str, str]] = {}
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for match in PY_ENUM_PATTERN.finditer(content):
            values: dict[str, str] = {}
            for line in match.group("body").splitlines():
                value = PY_VALUE_PATTERN.match(line)
                if value:
                    values[value.group("name")] = value.group("value")
            enums[match.group("name")] = values
    return enums


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    shared = parse_typescript(root / "packages/shared-types/src/enums.ts")
    backend = parse_python(sorted((root / "backend/app/enums").glob("*.py")))
    failures: list[str] = []
    for name, shared_values in shared.items():
        backend_values = backend.get(name)
        if backend_values is None:
            failures.append(f"缺少后端枚举: {name}")
            continue
        if shared_values != backend_values:
            failures.append(f"枚举值不一致: {name} shared={shared_values} backend={backend_values}")
    if failures:
        print("枚举同步检查失败:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print(f"枚举同步检查通过: {len(shared)} 个枚举")
    return 0


if __name__ == "__main__":
    sys.exit(main())
