import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CONFIG = Path(__file__).resolve().parents[2] / ".importlinter"


@pytest.mark.parametrize(
    ("contract", "modules", "allowed"),
    [
        (
            "layers",
            {
                "bootstrap.py": "import mindful.ui\nimport mindful.integration\n",
                "ui/__init__.py": "import mindful.application\n",
                "integration/__init__.py": "import mindful.application\n",
                "application/__init__.py": "import mindful.core\n",
            },
            True,
        ),
        ("layers", {"core/__init__.py": "import mindful.application\n"}, False),
        ("layers", {"ui/__init__.py": "import mindful.integration\n"}, False),
        ("layers", {"integration/__init__.py": "import mindful.ui\n"}, False),
        ("host-independence", {"core/__init__.py": "import anki\n"}, False),
        (
            "host-independence",
            {"application/__init__.py": "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import aqt\n"},
            False,
        ),
        (
            "host-independence",
            {
                "application/__init__.py": "import mindful.core.adapter\n",
                "core/adapter.py": "import PyQt6\n",
            },
            False,
        ),
        (
            "acyclic-siblings",
            {"core/first.py": "import mindful.core.second\n", "core/second.py": "import mindful.core.first\n"},
            False,
        ),
        ("acyclic-siblings", {"core/first.py": "import mindful.core.second\n", "core/second.py": ""}, True),
    ],
)
def test_import_contracts_in_isolated_package(tmp_path: Path, contract: str, modules: dict[str, str], *, allowed: bool) -> None:
    package = tmp_path / "mindful"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "bootstrap.py").write_text("", encoding="utf-8")
    for layer in ("core", "application", "integration", "ui"):
        (package / layer).mkdir()
        (package / layer / "__init__.py").write_text("", encoding="utf-8")
    for path, content in modules.items():
        (package / path).write_text(content, encoding="utf-8")

    command = shutil.which("lint-imports", path=str(Path(sys.executable).parent))
    assert command is not None
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)
    result = subprocess.run(
        [command, "--config", str(CONFIG), "--contract", contract, "--no-cache", "--no-logo"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (0 if allowed else 1), result.stdout + result.stderr
    assert ("KEPT" if allowed else "BROKEN") in result.stdout
    if "core/adapter.py" in modules:
        assert "mindful.application -> mindful.core.adapter" in result.stdout
