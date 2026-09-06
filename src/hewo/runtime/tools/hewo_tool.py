"""Minimal deterministic tool used by the HeWo runtime smoke."""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the HeWo runtime tool environment")
    parser.add_argument("--check", action="store_true", help="emit the smoke sentinel")
    args = parser.parse_args()
    if args.check:
        print("HEWO_TOOL_OK")
        return 0
    parser.error("use --check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
