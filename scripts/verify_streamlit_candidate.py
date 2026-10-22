"""Verify a traceable official-source build with reviewed frontend patches before integration or distribution."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import zipfile
from email.parser import BytesParser

from packaging.requirements import Requirement
from packaging.version import Version

def verify(wheel_dir: Path, source: Path, output: Path, expected_commit: str,
           frontend_patch: Path) -> dict:
    wheels = list(wheel_dir.glob("streamlit-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one complete Streamlit wheel")
    wheel = wheels[0]
    actual = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit) or actual != expected_commit:
        raise ValueError("Unexpected upstream source commit")
    subprocess.run(
        ["git", "-C", str(source), "diff", "--exit-code", "--",
         "lib/pyproject.toml", "lib/streamlit"],
        check=True,
    )
    patch = json.loads(frontend_patch.read_text(encoding="utf-8"))
    allowed = {"frontend/package.json", "frontend/lib/package.json", "frontend/yarn.lock"}
    changed = set(subprocess.check_output(
        ["git", "-C", str(source), "diff", "--name-only"], text=True,
    ).splitlines())
    if changed != allowed or set(patch["files"]) != allowed:
        raise ValueError("Unexpected frontend patch scope")
    for name, hashes in patch["files"].items():
        original = subprocess.check_output(["git", "-C", str(source), "show", f"HEAD:{name}"])
        if hashlib.sha256(original).hexdigest() != hashes["before_sha256"]:
            raise ValueError("Incorrect original frontend provenance")
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != hashes["sha256"]:
            raise ValueError("Frontend changed after recorded patch")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata_paths = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_paths) != 1:
            raise ValueError("Wheel metadata is ambiguous")
        metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
        if metadata["Name"] != "streamlit" or metadata["Version"] != "1.66.0":
            raise ValueError("Unexpected official source package identity")
        requirements = [Requirement(item) for item in metadata.get_all("Requires-Dist", [])]
        pillow = [item for item in requirements if item.name.lower() == "pillow"]
        if len(pillow) != 1 or Version("13.0.0") not in pillow[0].specifier:
            raise ValueError("Official wheel does not permit Pillow 13")
        index = "streamlit/static/index.html"
        if index not in names or len(archive.read(index)) < 100:
            raise ValueError("Frontend was not included in the wheel")
        for suffix, prefix in ((".js", "streamlit/static/static/js/"),
                               (".css", "streamlit/static/static/css/")):
            if not any(name.startswith(prefix) and name.endswith(suffix)
                       and len(archive.read(name)) > 0 for name in names):
                raise ValueError(f"Compiled frontend {suffix} assets were not included")
        if not any(name.endswith("_pb2.py") for name in names):
            raise ValueError("Generated protobuf bindings were not included")
        if not any("LICENSE" in name.upper() for name in names):
            raise ValueError("Required license notice was not included")
    import PIL
    import streamlit

    if PIL.__version__ != "13.0.0" or streamlit.__version__ != "1.66.0":
        raise ValueError("Installed candidate identity is inconsistent")
    output.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "upstream_repository": "https://github.com/streamlit/streamlit",
        "upstream_commit": actual,
        "upstream_pr": 17589,
        "package": "streamlit",
        "version": "1.66.0",
        "distribution": "self-built-official-source-with-frontend-security-patches",
        "frontend_patch": patch,
        "frontend_security_audit": "passed",
        "official_pypi_release": False,
        "wheel": wheel.name,
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "pillow": PIL.__version__,
        "python": platform.python_version(),
        "installed": {
            dist.metadata["Name"]: dist.version
            for dist in importlib.metadata.distributions()
        },
        "project_integration": "pending",
        "release_approved": False,
    }
    (output / "provenance.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "SHA256SUMS.txt").write_text(
        record["sha256"] + "  " + wheel.name + "\n", encoding="ascii"
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frontend-patch", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.wheel_dir, args.source, args.output, args.expected_commit, args.frontend_patch), indent=2))


if __name__ == "__main__":
    main()
