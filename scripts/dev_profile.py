"""Initialize a fresh Anki profile for a disposable development session."""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from aqt.profiles import ProfileManager

PROFILE = "Mindful Dev"
LANGUAGE = "en_US"


def create_manager(base: "Path") -> "ProfileManager":
    """Create Anki's profile manager only when initializing a session.

    Returns:
        The profile manager for the isolated base.
    """
    return import_module("aqt.profiles").ProfileManager(base)


def initialize_preferences(base: "Path") -> None:
    """Create non-interactive preferences without copying production settings.

    Raises:
        RuntimeError: The base is not fresh or the profile cannot be loaded.
    """
    if (base / "prefs21.db").exists() or (base / "prefs.db").exists():
        msg = "Refusing to initialize an existing Anki preferences database."
        raise RuntimeError(msg)
    manager = create_manager(base)
    try:
        result = manager.setupMeta()
        if not result.firstTime or result.loadError:
            msg = "Could not initialize fresh Anki preferences."
            raise RuntimeError(msg)
        manager.setLang(LANGUAGE)
        manager.create(PROFILE)
        if not manager.load(PROFILE) or manager.profile is None:
            msg = "Could not load the development profile."
            raise RuntimeError(msg)
        manager.meta["firstRun"] = False
        manager.clear_sync_auth()
        manager.profile["autoSync"] = False
        manager.profile["syncMedia"] = False
        manager.set_periodic_sync_media_minutes(0)
        manager.set_update_check(False)
        manager.save()
    finally:
        if manager.db is not None:
            manager.db.close()
