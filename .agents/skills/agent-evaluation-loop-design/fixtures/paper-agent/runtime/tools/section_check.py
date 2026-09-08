#!/usr/bin/env python3
"""Fixture leaf tool: report which required sections a draft is missing.

Deterministic, stateless, no network, no credentials. A real product Agent's
leaf tool looks like this: one job, explicit input and output, independently
verifiable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_SECTIONS = (
    "abstract",
    "introduction",
    "related work",
    "method",
    "experiments",
    "discussion",
    "conclusion",
    "references",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="draft Markdown file")
    parser.add_argument("--check", action="store_true", help="exit non-zero when sections are missing")
    args = parser.parse_args()
    try:
        text = args.draft.read_text(encoding="utf-8").lower()
    except OSError as exc:
        print(f"unreadable draft: {exc}", file=sys.stderr)
        return 2
    missing = [name for name in REQUIRED_SECTIONS if name not in text]
    print(json.dumps({"missing_sections": missing}, ensure_ascii=False, sort_keys=True))
    return 1 if (args.check and missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
