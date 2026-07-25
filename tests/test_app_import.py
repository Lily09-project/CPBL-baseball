import importlib.util
from pathlib import Path


def test_app_imports_without_crashing():
    assert Path("app.py").exists()
    spec = importlib.util.spec_from_file_location("cpbl_app", "app.py")
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
