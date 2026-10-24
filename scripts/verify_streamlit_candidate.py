"""Verify the official Streamlit PyPI wheel used by the product lockfiles."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile
from email.parser import BytesParser

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version


PACKAGE = "streamlit"
VERSION = "1.66.1"
WHEEL = "streamlit-1.66.1-py3-none-any.whl"
PYPI_JSON = "https://pypi.org/pypi/streamlit/1.66.1/json"
RELEASE_URL = "https://pypi.org/project/streamlit/1.66.1/"
SOURCE_RELEASE_URL = "https://github.com/streamlit/streamlit/releases/tag/1.66.1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_pypi_release() -> dict:
    request = Request(PYPI_JSON, headers={"User-Agent": "Lily09-project-release-verifier/1.0"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f"PyPI returned HTTP {response.status}")
        payload = json.load(response)
    if payload.get("info", {}).get("name", "").lower() != PACKAGE:
        raise ValueError("PyPI returned an unexpected project")
    if payload.get("info", {}).get("version") != VERSION:
        raise ValueError("PyPI returned an unexpected release")
    return payload


def verify(wheel_dir: Path, output: Path, release: dict | None = None) -> dict:
    wheels = list(wheel_dir.glob("streamlit-*.whl"))
    if len(wheels) != 1 or wheels[0].name != WHEEL:
        raise ValueError("Expected exactly the official Streamlit 1.66.1 universal wheel")
    wheel = wheels[0]
    release = release or fetch_pypi_release()
    file_records = [item for item in release.get("urls", []) if item.get("filename") == WHEEL]
    if len(file_records) != 1:
        raise ValueError("PyPI release metadata does not identify one official wheel")
    file_record = file_records[0]
    if file_record.get("packagetype") != "bdist_wheel":
        raise ValueError("PyPI artifact is not a wheel")
    if not file_record.get("url", "").startswith("https://files.pythonhosted.org/"):
        raise ValueError("Unexpected PyPI artifact host")
    expected_sha256 = file_record.get("digests", {}).get("sha256")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ValueError("PyPI did not provide a valid SHA256 digest")
    actual_sha256 = sha256(wheel)
    if actual_sha256 != expected_sha256:
        raise ValueError("Downloaded wheel does not match the official PyPI digest")

    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata_paths = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_paths) != 1:
            raise ValueError("Wheel metadata is ambiguous")
        metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
        if metadata["Name"].lower() != PACKAGE or metadata["Version"] != VERSION:
            raise ValueError("Unexpected Streamlit wheel identity")
        requires_python = metadata.get("Requires-Python")
        if not requires_python or Version("3.12") not in SpecifierSet(requires_python):
            raise ValueError("Wheel does not declare compatibility with Python 3.12")
        requirements = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
        pillow = [item for item in requirements if item.name.lower() == "pillow"]
        if len(pillow) != 1 or Version("13.0.0") not in pillow[0].specifier:
            raise ValueError("Official wheel does not permit Pillow 13.0.0")
        index = "streamlit/static/index.html"
        if index not in names or len(archive.read(index)) < 100:
            raise ValueError("Packaged Streamlit UI entry point is missing")
        for suffix, prefix in (
            (".js", "streamlit/static/static/js/"),
            (".css", "streamlit/static/static/css/"),
        ):
            assets = [
                name for name in names
                if name.startswith(prefix)
                and name.endswith(suffix)
                and archive.getinfo(name).file_size > 0
            ]
            if not assets:
                raise ValueError(f"Packaged Streamlit UI {suffix} assets are missing")
        if not any(name.endswith("_pb2.py") for name in names):
            raise ValueError("Generated protobuf bindings are missing")
        if not any(name.endswith("LICENSE") or name.endswith("LICENSE.txt") for name in names):
            raise ValueError("Package license notice is missing")

    output.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "distribution": "official-pypi-wheel",
        "package": PACKAGE,
        "version": VERSION,
        "release_url": RELEASE_URL,
        "source_release_url": SOURCE_RELEASE_URL,
        "pypi_metadata_url": PYPI_JSON,
        "pypi_file_url": file_record["url"],
        "wheel": WHEEL,
        "sha256": actual_sha256,
        "python_version_tested": "3.12",
        "pillow_13_compatible": True,
        "official_pypi_release": True,
        "integrity_check": "Downloaded wheel SHA256 matches the official PyPI release JSON",
        "custom_source_build": False,
        "product_release_approved": False,
    }
    (output / "provenance.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "SHA256SUMS.txt").write_text(
        actual_sha256 + "  " + wheel.name + "\n", encoding="ascii"
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.wheel_dir, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
