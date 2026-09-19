from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from src.public_release_manifest import verify_public_release_manifest_file


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="驗證 CPBL 公開資料發布包的完整性")
    parser.add_argument("manifest", help="public_release_manifest.json 路徑")
    parser.add_argument("--root", type=Path, help="專案根目錄；預設使用目前 CPBL 專案")
    args = parser.parse_args(argv)

    try:
        result = verify_public_release_manifest_file(args.manifest, root=args.root)
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        print(
            json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
