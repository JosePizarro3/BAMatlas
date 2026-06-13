from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import yaml


def check_yaml(paths: list[str]) -> int:
    has_errors = False
    for raw_path in paths:
        path = Path(raw_path)
        try:
            with path.open("r", encoding="utf-8") as handle:
                yaml.safe_load(handle)
        except Exception as exc:
            print(f"{path}: invalid YAML: {exc}")
            has_errors = True
    return 1 if has_errors else 0


def check_toml(paths: list[str]) -> int:
    has_errors = False
    for raw_path in paths:
        path = Path(raw_path)
        try:
            with path.open("rb") as handle:
                tomllib.load(handle)
        except Exception as exc:
            print(f"{path}: invalid TOML: {exc}")
            has_errors = True
    return 1 if has_errors else 0


def check_end_of_file(paths: list[str]) -> int:
    has_errors = False
    for raw_path in paths:
        path = Path(raw_path)
        content = path.read_bytes()
        if content and not content.endswith(b"\n"):
            print(f"{path}: file does not end with a newline")
            has_errors = True
    return 1 if has_errors else 0


def check_trailing_whitespace(paths: list[str]) -> int:
    has_errors = False
    for raw_path in paths:
        path = Path(raw_path)
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
            if line.rstrip(" \t") != line:
                print(f"{path}:{line_number}: trailing whitespace")
                has_errors = True
    return 1 if has_errors else 0


def check_merge_conflict(paths: list[str]) -> int:
    markers = ("<<<<<<< ", "=======", ">>>>>>> ")
    has_errors = False
    for raw_path in paths:
        path = Path(raw_path)
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1,
        ):
            if any(line.startswith(marker) for marker in markers):
                print(f"{path}:{line_number}: merge conflict marker detected")
                has_errors = True
    return 1 if has_errors else 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: run.py <yaml|toml|eof|trailing-whitespace|merge-conflict> [paths...]")
        return 2

    command = argv[1]
    paths = argv[2:]
    handlers = {
        "yaml": check_yaml,
        "toml": check_toml,
        "eof": check_end_of_file,
        "trailing-whitespace": check_trailing_whitespace,
        "merge-conflict": check_merge_conflict,
    }
    handler = handlers.get(command)
    if handler is None:
        print(f"unknown command: {command}")
        return 2
    return handler(paths)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
