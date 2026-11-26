import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    dev_profile = importlib.import_module("scripts.dev_profile")
finally:
    sys.path.pop(0)


def test_fresh_profile_is_initialized_without_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = MagicMock()
    manager.meta = {"firstRun": True}
    manager.profile = {"syncKey": None, "autoSync": True, "syncMedia": True}
    manager.setupMeta.return_value = SimpleNamespace(firstTime=True, loadError=False)
    manager.load.return_value = True
    monkeypatch.setattr(dev_profile, "create_manager", lambda base: manager)

    dev_profile.initialize_preferences(tmp_path)

    manager.setLang.assert_called_once_with("en_US")
    manager.create.assert_called_once_with("Mindful Dev")
    manager.load.assert_called_once_with("Mindful Dev")
    manager.clear_sync_auth.assert_called_once_with()
    manager.set_update_check.assert_called_once_with(False)
    manager.set_periodic_sync_media_minutes.assert_called_once_with(0)
    assert manager.meta["firstRun"] is False
    assert manager.profile["autoSync"] is False
    assert manager.profile["syncMedia"] is False
    manager.save.assert_called_once_with()
    manager.db.close.assert_called_once_with()


def test_existing_preferences_are_not_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    preferences = tmp_path / "prefs21.db"
    preferences.write_bytes(b"existing")
    create = MagicMock()
    monkeypatch.setattr(dev_profile, "create_manager", create)
    with pytest.raises(RuntimeError, match="existing"):
        dev_profile.initialize_preferences(tmp_path)
    create.assert_not_called()
    assert preferences.read_bytes() == b"existing"


def test_preferences_close_if_initialization_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = MagicMock()
    manager.setupMeta.return_value = SimpleNamespace(firstTime=True, loadError=False)
    manager.setLang.side_effect = RuntimeError("initialization failed")
    monkeypatch.setattr(dev_profile, "create_manager", lambda base: manager)
    with pytest.raises(RuntimeError, match="initialization failed"):
        dev_profile.initialize_preferences(tmp_path)
    manager.db.close.assert_called_once_with()
    manager.save.assert_not_called()
