"""Apply reviewed frontend dependency updates without editing Python metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

OVERRIDES = {
    "katex": "0.18.10",
    "markdown-it": "14.3.3",
    "@ungap/structured-clone": "1.3.1",
    "http-cache-semantics": "4.3.0",
    "vite": "8.3.5",
}
ALLOWED_FILES = (
    "frontend/package.json",
    "frontend/lib/package.json",
    "frontend/yarn.lock",
)


def patch_manifests(source: Path) -> None:
    root_path = source / "frontend/package.json"
    lib_path = source / "frontend/lib/package.json"
    root = json.loads(root_path.read_text(encoding="utf-8"))
    lib = json.loads(lib_path.read_text(encoding="utf-8"))
    if root.get("packageManager") != "yarn@4.13.0":
        raise ValueError("Unexpected upstream frontend toolchain")
    if lib.get("dependencies", {}).get("katex") != "^0.16.47":
        raise ValueError("Unexpected upstream KaTeX requirement; review before patching")
    root.setdefault("resolutions", {}).update(OVERRIDES)
    lib["dependencies"]["katex"] = OVERRIDES["katex"]
    root_path.write_text(json.dumps(root, indent=2) + "\n", encoding="utf-8")
    lib_path.write_text(json.dumps(lib, indent=2) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    before = {name: digest(source / name) for name in ALLOWED_FILES}
    patch_manifests(source)
    environment = dict(os.environ, YARN_ENABLE_IMMUTABLE_INSTALLS="false")
    subprocess.run(
        ["yarn", "install", "--mode=skip-build"],
        cwd=source / "frontend", env=environment, check=True,
    )
    subprocess.run(
        ["yarn", "install", "--immutable"],
        cwd=source / "frontend", check=True,
    )
    changed = subprocess.check_output(
        ["git", "-C", str(source), "diff", "--name-only"], text=True,
    ).splitlines()
    if set(changed) != set(ALLOWED_FILES):
        raise ValueError(f"Unexpected upstream modifications: {changed}")
    subprocess.run(
        ["git", "-C", str(source), "diff", "--exit-code", "--",
         "lib/pyproject.toml", "lib/streamlit"], check=True,
    )
    report = {
        "schema_version": 1,
        "distribution": "self-built-official-source-with-frontend-security-patches",
        "python_metadata_modified": False,
        "overrides": OVERRIDES,
        "files": {
            name: {"before_sha256": before[name], "sha256": digest(source / name)}
            for name in ALLOWED_FILES
        },
        "security_audit": "pending",
        "release_approved": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
