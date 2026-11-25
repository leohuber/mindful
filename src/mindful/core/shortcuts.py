"""Resolve the configured keyboard shortcut for the edit action."""

import re

DEFAULT_EDIT_NOTE_SHORTCUT = "Ctrl+Shift+O"

_MODIFIERS = {"ctrl", "shift", "alt", "meta"}
_NAMED_KEYS = {
    "backspace",
    "del",
    "delete",
    "down",
    "end",
    "enter",
    "esc",
    "escape",
    "home",
    "ins",
    "insert",
    "left",
    "pgdown",
    "pgup",
    "pagedown",
    "pageup",
    "return",
    "right",
    "space",
    "tab",
    "up",
}
_FUNCTION_KEY = re.compile(r"f([1-9]|[12]\d|3[0-5])")


def _is_valid(shortcut: str) -> bool:
    parts = [part.strip().lower() for part in shortcut.split("+")]
    *modifiers, key = parts
    if any(part not in _MODIFIERS for part in modifiers) or len(set(modifiers)) != len(modifiers):
        return False
    if len(key) == 1:
        return key.isprintable() and not key.isspace()
    return key in _NAMED_KEYS or _FUNCTION_KEY.fullmatch(key) is not None


def resolve_edit_note_shortcut(config: object) -> str:
    """Read the edit action shortcut from the add-on configuration.

    Returns:
        The configured shortcut, an empty string to disable it, or the default when it is missing or invalid.
    """
    value = config.get("edit_note_shortcut") if isinstance(config, dict) else None
    if not isinstance(value, str):
        return DEFAULT_EDIT_NOTE_SHORTCUT
    shortcut = value.strip()
    if not shortcut:
        return ""
    return shortcut if _is_valid(shortcut) else DEFAULT_EDIT_NOTE_SHORTCUT
