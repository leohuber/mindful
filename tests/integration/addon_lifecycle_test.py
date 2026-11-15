import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest

PACKAGE_PATH = Path(__file__).resolve().parents[2] / "src" / "mindful" / "__init__.py"


def load_package(monkeypatch: pytest.MonkeyPatch, name: str) -> Mock:
    bootstrap = ModuleType(f"{name}.bootstrap")
    initialize = Mock()
    bootstrap.initialize = initialize
    monkeypatch.setitem(sys.modules, bootstrap.__name__, bootstrap)
    spec = importlib.util.spec_from_file_location(name, PACKAGE_PATH, submodule_search_locations=[str(PACKAGE_PATH.parent)])
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return initialize


@pytest.mark.parametrize("aqt_present", [False, True])
def test_standalone_import_does_not_initialize(monkeypatch: pytest.MonkeyPatch, *, aqt_present: bool) -> None:
    monkeypatch.delitem(sys.modules, "aqt", raising=False)
    if aqt_present:
        aqt = ModuleType("aqt")
        aqt.mw = None
        monkeypatch.setitem(sys.modules, "aqt", aqt)

    initialize = load_package(monkeypatch, "mindful_standalone_test")

    initialize.assert_not_called()
    if not aqt_present:
        assert "aqt" not in sys.modules


def test_host_import_initializes_without_collection_access(monkeypatch: pytest.MonkeyPatch) -> None:
    class MainWindow:
        @property
        def col(self) -> None:
            pytest.fail("collection accessed during startup")

    aqt = ModuleType("aqt")
    aqt.mw = MainWindow()
    monkeypatch.setitem(sys.modules, "aqt", aqt)

    initialize = load_package(monkeypatch, "mindful_host_test")

    initialize.assert_called_once_with()


def test_numeric_addon_directory_loads_relative_bootstrap(tmp_path: Path) -> None:
    shutil.copytree(PACKAGE_PATH.parent, tmp_path / "123456789")
    script = """
import importlib, sys, types
sys.path.insert(0, sys.argv[1])
aqt = types.ModuleType("aqt")
aqt.mw = object()
sys.modules["aqt"] = aqt
importlib.import_module("123456789")
assert "123456789.bootstrap" in sys.modules
assert "mindful.bootstrap" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", script, str(tmp_path)], check=True)


def test_standalone_command() -> None:
    command = shutil.which("mindful", path=str(Path(sys.executable).parent))
    assert command is not None
    result = subprocess.run([command], check=True, capture_output=True, text=True)
    assert result.stdout == "Hello from mindful!\n"
    assert result.stderr == ""
