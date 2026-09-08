#!/usr/bin/env python3
"""Shared normative helpers for the agent-evaluation-loop-design skill.

Implements the canonical JSON form, the hash definitions, the path-safety rules
and the dependency-free ``agent.yaml`` reader described in
``../references/evaluation-contract.md`` and
``../references/agent-architecture-schema.md``.

Standard library only. No network access, no credential access, no provider
calls. Never writes into a product runtime directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

HEX64 = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


class DocumentError(Exception):
    """A JSON document is missing, unreadable or not well formed."""


class PathSafetyError(Exception):
    """A path violated the lexical or realpath safety rules."""


# --------------------------------------------------------------------------
# Canonical JSON and hashing
# --------------------------------------------------------------------------


def decimal_text(value: Decimal) -> str:
    """Plain, non-exponential decimal text preserving the source digits."""
    return format(value, "f")


def _canonical_chunks(value: Any, out: list[bytes]) -> None:
    if value is True:
        out.append(b"true")
    elif value is False:
        out.append(b"false")
    elif value is None:
        out.append(b"null")
    elif isinstance(value, int):
        out.append(str(value).encode("utf-8"))
    elif isinstance(value, Decimal):
        out.append(decimal_text(value).encode("utf-8"))
    elif isinstance(value, float):
        # Only reached when a caller parsed without exact decimals.
        out.append(decimal_text(Decimal(repr(value))).encode("utf-8"))
    elif isinstance(value, str):
        out.append(json.dumps(value, ensure_ascii=False).encode("utf-8"))
    elif isinstance(value, (list, tuple)):
        out.append(b"[")
        for index, item in enumerate(value):
            if index:
                out.append(b",")
            _canonical_chunks(item, out)
        out.append(b"]")
    elif isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise DocumentError(f"non-string object key: {key!r}")
        out.append(b"{")
        for index, key in enumerate(sorted(value)):
            if index:
                out.append(b",")
            out.append(json.dumps(key, ensure_ascii=False).encode("utf-8"))
            out.append(b":")
            _canonical_chunks(value[key], out)
        out.append(b"}")
    else:
        raise DocumentError(f"value is not canonicalizable: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Canonical JSON bytes: UTF-8, sorted keys, no insignificant whitespace."""
    out: list[bytes] = []
    _canonical_chunks(value, out)
    return b"".join(out)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def promoted_result_sha256(result: Any) -> str:
    """Hash of a result document with the top-level ``promotion`` key removed."""
    if not isinstance(result, dict):
        raise DocumentError("result document is not an object")
    stripped = {key: value for key, value in result.items() if key != "promotion"}
    return canonical_sha256(stripped)


# --------------------------------------------------------------------------
# JSON loading with exact decimals
# --------------------------------------------------------------------------


def load_json_exact(path: Path) -> Any:
    """Load JSON using exact decimals so metric arithmetic is reproducible."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocumentError(f"unreadable: {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise DocumentError(f"not valid UTF-8: {path}: {exc}") from exc
    try:
        return json.loads(text, parse_float=Decimal)
    except json.JSONDecodeError as exc:
        raise DocumentError(f"not well-formed JSON: {path}: {exc}") from exc


def _pretty_chunks(value: Any, indent: int, level: int, out: list[str]) -> None:
    pad = " " * (indent * level)
    inner_pad = " " * (indent * (level + 1))
    if value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif value is None:
        out.append("null")
    elif isinstance(value, int):
        out.append(str(value))
    elif isinstance(value, Decimal):
        out.append(decimal_text(value))
    elif isinstance(value, float):
        out.append(decimal_text(Decimal(repr(value))))
    elif isinstance(value, str):
        out.append(json.dumps(value, ensure_ascii=False))
    elif isinstance(value, (list, tuple)):
        if not value:
            out.append("[]")
            return
        out.append("[\n")
        for index, item in enumerate(value):
            if index:
                out.append(",\n")
            out.append(inner_pad)
            _pretty_chunks(item, indent, level + 1, out)
        out.append("\n" + pad + "]")
    elif isinstance(value, dict):
        if not value:
            out.append("{}")
            return
        out.append("{\n")
        for index, key in enumerate(sorted(value)):
            if not isinstance(key, str):
                raise DocumentError(f"non-string object key: {key!r}")
            if index:
                out.append(",\n")
            out.append(inner_pad + json.dumps(key, ensure_ascii=False) + ": ")
            _pretty_chunks(value[key], indent, level + 1, out)
        out.append("\n" + pad + "}")
    else:
        raise DocumentError(f"value is not serializable: {type(value).__name__}")


def dump_canonical_json(value: Any, indent: int = 2) -> str:
    """Readable, key-sorted JSON that preserves the exact decimal digits.

    Round-trip stable: reloading the output with ``load_json_exact`` and dumping
    it again yields byte-identical text, so hashes computed over the in-memory
    document match hashes computed after a reload.
    """
    out: list[str] = []
    _pretty_chunks(value, indent, 0, out)
    return "".join(out)


# --------------------------------------------------------------------------
# Path safety
# --------------------------------------------------------------------------


def lexical_relative_check(relative: str) -> PurePosixPath:
    """Reject absolute, traversing, NUL-bearing and drive/UNC-prefixed paths."""
    if not isinstance(relative, str) or not relative:
        raise PathSafetyError("empty or non-string relative path")
    if "\0" in relative:
        raise PathSafetyError("relative path contains NUL")
    if relative.startswith("/") or relative.startswith("\\"):
        raise PathSafetyError(f"absolute relative path: {relative!r}")
    if _WINDOWS_DRIVE.match(relative) or relative.startswith("\\\\"):
        raise PathSafetyError(f"drive or UNC prefixed path: {relative!r}")
    pure = PurePosixPath(relative)
    if pure.is_absolute():
        raise PathSafetyError(f"absolute relative path: {relative!r}")
    for part in pure.parts:
        if part == "..":
            raise PathSafetyError(f"parent traversal in path: {relative!r}")
    return pure


def assert_no_symlink_within(base: Path, target: Path) -> None:
    """Refuse a symlink at ``target`` or at any component below ``base``."""
    base_resolved = base.resolve()
    current = target
    seen: list[Path] = []
    while True:
        seen.append(current)
        try:
            same = current.resolve() == base_resolved
        except OSError as exc:
            raise PathSafetyError(f"unresolvable path component: {current}: {exc}") from exc
        if same:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    for item in seen:
        if item.resolve() == base_resolved:
            continue
        if item.is_symlink():
            raise PathSafetyError(f"symlink is not allowed: {item}")


def safe_child_path(base: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``base`` with lexical + realpath + symlink checks."""
    lexical_relative_check(relative)
    base_resolved = base.resolve()
    candidate = base_resolved / relative
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PathSafetyError(f"cannot resolve {relative!r} under {base_resolved}: {exc}") from exc
    if not is_within(resolved, base_resolved):
        raise PathSafetyError(f"{relative!r} resolves outside {base_resolved}")
    assert_no_symlink_within(base_resolved, candidate)
    return resolved


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def safe_input_file(path: Path) -> Path:
    """Validate an explicitly supplied input file before it is read."""
    if str(path) == "":
        raise PathSafetyError("empty input path")
    if "\0" in str(path):
        raise PathSafetyError("input path contains NUL")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PathSafetyError(f"input path does not resolve: {path}: {exc}") from exc
    if path.is_symlink():
        raise PathSafetyError(f"input path is a symlink: {path}")
    if not resolved.is_file():
        raise PathSafetyError(f"input path is not a regular file: {path}")
    return resolved


def safe_output_file(path: Path) -> Path:
    """Validate an explicit report destination: never a symlink, parent must exist."""
    if str(path) == "":
        raise PathSafetyError("empty output path")
    if "\0" in str(path):
        raise PathSafetyError("output path contains NUL")
    if path.is_symlink():
        raise PathSafetyError(f"output path is a symlink: {path}")
    parent = path.parent
    try:
        parent_resolved = parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PathSafetyError(f"output directory does not exist: {parent}: {exc}") from exc
    if not parent_resolved.is_dir():
        raise PathSafetyError(f"output parent is not a directory: {parent}")
    return parent_resolved / path.name


# --------------------------------------------------------------------------
# Atomic writes
# --------------------------------------------------------------------------


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write via a temporary file in the destination directory plus replace."""
    destination = safe_output_file(path)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=str(destination.parent),
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


# --------------------------------------------------------------------------
# agent.yaml
# --------------------------------------------------------------------------


def parse_agent_yaml(path: Path) -> dict[str, str]:
    """Read the simple ``key: value`` manifest without a third-party parser."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocumentError(f"unreadable agent manifest: {path}: {exc}") from exc
    values: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise DocumentError(f"{path}:{number}: expected 'key: value'")
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not key:
            raise DocumentError(f"{path}:{number}: empty key")
        values[key] = value
    return values


# --------------------------------------------------------------------------
# Metric arithmetic
# --------------------------------------------------------------------------


def as_decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise DocumentError(f"{label} must be a number, not a boolean")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(repr(value))
    raise DocumentError(f"{label} must be a number, got {type(value).__name__}")


def exact_mean(values: Iterable[Decimal]) -> Decimal:
    items = list(values)
    if not items:
        raise DocumentError("cannot take the mean of zero samples")
    total = Decimal(0)
    for item in items:
        total += item
    return total / Decimal(len(items))


def slug(text: str) -> str:
    """Deterministic, Mermaid-safe identifier fragment."""
    lowered = "".join(char if char.isascii() and char.isalnum() else "_" for char in text.lower())
    collapsed = re.sub(r"_+", "_", lowered).strip("_")
    return collapsed or "unnamed"
