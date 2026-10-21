"""Install a verified wheel with a project lock in an isolated CI environment."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import os
import venv

LOCKS = {
    "CPBL-baseball": "requirements.lock.txt",
    "market-anomaly-dashboard": "requirements-dev.lock.txt",
    "aqi-anomaly-dashboard": "requirements-lock-py312.txt",
}


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", choices=LOCKS, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    manifests = list(args.candidate.rglob("provenance.json"))
    wheels = list(args.candidate.rglob("streamlit-*.whl"))
    if len(manifests) != 1 or len(wheels) != 1:
        raise ValueError("Candidate wheel or provenance is ambiguous")
    wheel = wheels[0].resolve()
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("Candidate wheel checksum mismatch")
    if manifest["distribution"] != "self-built-unreleased-official-source":
        raise ValueError("Candidate provenance does not identify the build")
    args.output.mkdir(parents=True, exist_ok=True)
    environment = args.output.resolve() / "venv"
    venv.EnvBuilder(with_pip=True).create(environment)
    python = str(environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    lines = (project / LOCKS[args.repo]).read_text(encoding="utf-8-sig").splitlines()
    candidate_lines = [
        line for line in lines
        if not line.lower().startswith(("streamlit==", "pillow=="))
    ]
    candidate_lines += [str(wheel), "Pillow==13.0.0"]
    requirements = args.output.resolve() / "integration-requirements.txt"
    requirements.write_text("\n".join(candidate_lines) + "\n", encoding="utf-8")
    run([python, "-m", "pip", "install", "pip==26.2.1", "pip-audit==2.10.1"], project)
    run([python, "-m", "pip", "install", "-r", str(requirements)], project)
    run([python, "-m", "pip", "check"], project)
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
        "candidate_sha256": manifest["sha256"],
        "tests": "passed",
        "audit": "passed",
        "project_release_approved": False,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
