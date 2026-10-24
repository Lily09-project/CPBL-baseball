"""Keep published install ranges and reproducible environments consistent."""
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


LOCK_FILES = ["requirements.lock.txt"]


def read_requirements(path):
    return [
        Requirement(line.strip())
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-"))
    ]


@pytest.mark.parametrize("lock_path", LOCK_FILES)
def test_runtime_requirements_match_the_reproducible_lock(lock_path):
    locked = {canonicalize_name(item.name): item for item in read_requirements(lock_path)}
    for requirement in read_requirements("requirements.txt"):
        if requirement.marker is not None and not requirement.marker.evaluate({"python_version": "3.12"}):
            continue
        name = canonicalize_name(requirement.name)
        assert name in locked, f"{lock_path} is missing {name}"
        pins = list(locked[name].specifier)
        assert len(pins) == 1 and pins[0].operator == "==", f"{name} is not pinned"
        assert requirement.specifier.contains(pins[0].version), (
            f"{lock_path}: {name} {pins[0].version} violates {requirement.specifier}"
        )

@pytest.mark.parametrize("lock_path", LOCK_FILES)
@pytest.mark.parametrize(
    ("name", "floor", "unsafe_version"),
    [("urllib3", "2.8.0", "2.7.0"), ("certifi", "2026.10.19", "2026.6.17")],
)
def test_security_floors_cannot_regress(lock_path, name, floor, unsafe_version):
    direct = {
        canonicalize_name(item.name): item for item in read_requirements("requirements.txt")
    }
    locked = {
        canonicalize_name(item.name): item for item in read_requirements(lock_path)
    }
    assert name in direct, f"Missing explicit security floor for {name}"
    assert direct[name].specifier.contains(floor)
    assert not direct[name].specifier.contains(unsafe_version)
    pins = list(locked[name].specifier)
    assert len(pins) == 1 and pins[0].operator == "=="
    assert Requirement(f"{name}>={floor}").specifier.contains(pins[0].version)


def test_web_dependencies_are_pinned_exactly_and_locked():
    import json

    package = json.loads(Path("web/package.json").read_text(encoding="utf-8"))
    lock = json.loads(Path("web/package-lock.json").read_text(encoding="utf-8"))
    for section in ("dependencies", "devDependencies"):
        for name, version in package[section].items():
            assert version[0].isdigit(), f"{name} must be pinned exactly, got {version}"
            assert lock["packages"][f"node_modules/{name}"]["version"] == version
