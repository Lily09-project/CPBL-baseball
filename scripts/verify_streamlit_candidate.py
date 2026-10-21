"""Verify an unmodified official Streamlit build before integration or distribution."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import zipfile
from email.parser import BytesParser

from packaging.requirements import Requirement
from packaging.version import Version

SOURCE_SHA = "81bdb8a8a207691f17ec94df9eabc96b6b50ea7a"


def verify(wheel_dir: Path, source: Path, output: Path) -> dict:
    wheels = list(wheel_dir.glob("streamlit-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one complete Streamlit wheel")
    wheel = wheels[0]
    actual = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != SOURCE_SHA:
        raise ValueError("Unexpected upstream source commit")
    subprocess.run(
        ["git", "-C", str(source), "diff", "--exit-code", "--",
         "lib/pyproject.toml", "lib/streamlit"],
        check=True,
    )
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
        if not any(name.startswith("streamlit/static/assets/") for name in names):
            raise ValueError("Compiled frontend assets were not included")
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
        "upstream_commit": SOURCE_SHA,
        "upstream_pr": 17589,
        "package": "streamlit",
        "version": "1.66.0",
        "distribution": "self-built-unreleased-official-source",
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
    args = parser.parse_args()
    print(json.dumps(verify(args.wheel_dir, args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
