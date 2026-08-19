from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from src.scouting_report import verify_report_manifest_file


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="驗證 CPBL 球探報告 Manifest 的完整性")
    parser.add_argument("manifest", help="要驗證的 .manifest.json 檔案路徑")
    args = parser.parse_args(argv)

    try:
        result = verify_report_manifest_file(args.manifest)
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        error = {"valid": False, "error": str(exc)}
        print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
