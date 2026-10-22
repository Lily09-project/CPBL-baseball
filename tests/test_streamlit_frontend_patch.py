import json
from pathlib import Path

import pytest

from scripts.patch_streamlit_frontend import OVERRIDES, patch_manifests


def _source(tmp_path: Path) -> Path:
    (tmp_path / "frontend/lib").mkdir(parents=True)
    (tmp_path / "frontend/package.json").write_text(json.dumps({
        "packageManager": "yarn@4.13.0",
        "resolutions": {"existing-package": "1.2.3"},
    }), encoding="utf-8")
    (tmp_path / "frontend/lib/package.json").write_text(json.dumps({
        "dependencies": {"katex": "^0.16.47", "unchanged": "^2.0.0"},
    }), encoding="utf-8")
    return tmp_path


def test_patch_preserves_unrelated_requirements(tmp_path: Path) -> None:
    source = _source(tmp_path)
    patch_manifests(source)
    root = json.loads((source / "frontend/package.json").read_text())
    lib = json.loads((source / "frontend/lib/package.json").read_text())
    assert root["resolutions"] == {"existing-package": "1.2.3", **OVERRIDES}
    assert lib["dependencies"] == {"katex": "0.18.10", "unchanged": "^2.0.0"}
    assert {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()} == {
        "frontend/package.json", "frontend/lib/package.json",
    }


def test_patch_refuses_unreviewed_upstream_requirement(tmp_path: Path) -> None:
    source = _source(tmp_path)
    path = source / "frontend/lib/package.json"
    path.write_text(json.dumps({"dependencies": {"katex": "^0.19.0"}}))
    with pytest.raises(ValueError, match="Unexpected upstream KaTeX"):
        patch_manifests(source)


def test_patch_refuses_unreviewed_toolchain(tmp_path: Path) -> None:
    source = _source(tmp_path)
    (source / "frontend/package.json").write_text(json.dumps({"packageManager": "yarn@5.0.0"}))
    with pytest.raises(ValueError, match="Unexpected upstream frontend toolchain"):
        patch_manifests(source)


def test_security_overrides_use_published_compatible_maintenance_releases() -> None:
    assert OVERRIDES["http-cache-semantics"] == "4.3.0"
    assert OVERRIDES["vite"] == "8.3.5"
    # Do not force the ~4.4.x glTF consumers onto a different loaders minor.
    assert not any(name.startswith("@loaders.gl/") for name in OVERRIDES)
    assert "braces" not in OVERRIDES
    assert "sprintf-js" not in OVERRIDES
