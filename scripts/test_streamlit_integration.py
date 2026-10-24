"""Install the official Streamlit wheel with a product lock in isolated CI."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import os
import venv
import zipfile
from email.parser import BytesParser

LOCKS = {
    "CPBL-baseball": "requirements.lock.txt",
    "market-anomaly-dashboard": "requirements-dev.lock.txt",
    "aqi-anomaly-dashboard": "requirements-lock-py312.txt",
}
STREAMLIT_VERSION = "1.66.1"
PILLOW_VERSION = "13.0.0"


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def verify_candidate(candidate: Path) -> tuple[Path, dict]:
    manifests = list(candidate.rglob("provenance.json"))
    wheels = list(candidate.rglob("streamlit-*.whl"))
    if len(manifests) != 1 or len(wheels) != 1:
        raise ValueError("Official wheel or provenance is ambiguous")
    wheel = wheels[0].resolve()
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if manifest.get("distribution") != "official-pypi-wheel":
        raise ValueError("Candidate provenance is not for the official PyPI wheel")
    if manifest.get("version") != STREAMLIT_VERSION or manifest.get("wheel") != wheel.name:
        raise ValueError("Candidate provenance identifies an unexpected release")
    if digest != manifest.get("sha256"):
        raise ValueError("Official wheel checksum does not match provenance")
    with zipfile.ZipFile(wheel) as archive:
        metadata_paths = [
            name for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_paths) != 1:
            raise ValueError("Official wheel metadata is ambiguous")
        metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
    if (
        metadata.get("Name", "").lower() != "streamlit"
        or metadata.get("Version") != STREAMLIT_VERSION
    ):
        raise ValueError("Unexpected installed Streamlit wheel")
    return wheel, manifest


def lock_version(lines: list[str], package: str) -> str:
    matches = [
        line.split("==", 1)[1].strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
        and line.split("==", 1)[0].strip().lower() == package.lower()
        and "==" in line
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one {package} pin in project lock")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", choices=LOCKS, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    wheel, manifest = verify_candidate(args.candidate)
    args.output.mkdir(parents=True, exist_ok=True)
    environment = args.output.resolve().parent / ".official-streamlit-integration-venv"
    venv.EnvBuilder(with_pip=True).create(environment)
    python = str(environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    lines = (project / LOCKS[args.repo]).read_text(encoding="utf-8-sig").splitlines()
    if lock_version(lines, "streamlit") != STREAMLIT_VERSION:
        raise ValueError("Project lock does not pin the verified official Streamlit release")
    if lock_version(lines, "pillow") != PILLOW_VERSION:
        raise ValueError("Project lock does not pin the audited Pillow release")
    candidate_lines = [
        line for line in lines
        if line.split("==", 1)[0].strip().lower() not in {"streamlit", "pillow"}
    ]
    candidate_lines += [str(wheel), f"Pillow=={PILLOW_VERSION}"]
    requirements = args.output.resolve() / "integration-requirements.txt"
    requirements.write_text("\n".join(candidate_lines) + "\n", encoding="utf-8")
    run([python, "-m", "pip", "install", "pip==26.2.1", "pip-audit==2.10.1"], project)
    run([python, "-m", "pip", "install", "-r", str(requirements)], project)
    run([python, "-m", "pip", "check"], project)
    identity_command = (
        "import PIL, streamlit; "
        "print(streamlit.__version__); "
        "print(PIL.__version__)"
    )
    identity = subprocess.check_output(
        [python, "-c", identity_command],
        text=True,
    ).splitlines()
    if identity != [STREAMLIT_VERSION, PILLOW_VERSION]:
        raise ValueError(f"Unexpected installed runtime versions: {identity}")
    if args.repo != "CPBL-baseball":
        run([python, "run_all.py", "--mode", "sample"], project)
    run([python, "-W", "error", "-m", "pytest", "-q", "-p", "no:cacheprovider"], project)
    run([python, "-m", "pip_audit", "--local", "--strict", "--progress-spinner", "off"], project)
    installed = subprocess.check_output([python, "-m", "pip", "freeze"], text=True)
    (args.output / "installed.txt").write_text(installed, encoding="utf-8")
    (args.output / "result.json").write_text(json.dumps({
        "repository": args.repo,
        "source_sha": subprocess.check_output(
            ["git", "-C", str(project), "rev-parse", "HEAD"], text=True
        ).strip(),
        "streamlit_distribution": manifest["distribution"],
        "streamlit_version": STREAMLIT_VERSION,
        "streamlit_sha256": manifest["sha256"],
        "pillow_version": PILLOW_VERSION,
        "tests": "passed",
        "strict_runtime_audit": "passed",
        "project_release_approved": False,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
