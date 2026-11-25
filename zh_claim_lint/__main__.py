"""Command-line interface."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from . import check


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="zh-claim-lint",
        description="Compare structured claims in a Chinese draft with a UTF-8 reference.")
    parser.add_argument("source", type=Path)
    parser.add_argument("draft", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if argv is None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        source = args.source.read_bytes().decode("utf-8-sig")
        draft = args.draft.read_bytes().decode("utf-8-sig")
        if not source.strip():
            raise ValueError("source is empty")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: {exc}\n")
    findings = check(source, draft)
    if args.format == "json":
        print(json.dumps({"schema_version": 1, "findings": [asdict(f) for f in findings]},
                         ensure_ascii=True, indent=2))
    elif findings:
        for f in findings:
            print(f"{args.draft}:{f.line}:{f.column}: [{f.kind}] 原文未找到：{f.text}")
    else:
        print("未发现需复核的结构化声明。")
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
