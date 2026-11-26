"""Resolve the configured keyboard shortcuts for Mindful's actions."""

import re

DEFAULT_EDIT_NOTE_SHORTCUT = "Ctrl+Shift+O"
DEFAULT_PREVIOUS_NOTE_SHORTCUT = "Ctrl+Alt+Left"
DEFAULT_NEXT_NOTE_SHORTCUT = "Ctrl+Alt+Right"

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


def _resolve(config: object, key: str, default: str) -> str:
    value = config.get(key) if isinstance(config, dict) else None
    if not isinstance(value, str):
        return default
    shortcut = value.strip()
    if not shortcut:
        return ""
    return shortcut if _is_valid(shortcut) else default


def resolve_edit_note_shortcut(config: object) -> str:
    """Read the edit action shortcut from the add-on configuration.

    Returns:
        The configured shortcut, an empty string to disable it, or the default when it is missing or invalid.
    """
    return _resolve(config, "edit_note_shortcut", DEFAULT_EDIT_NOTE_SHORTCUT)


def resolve_previous_note_shortcut(config: object) -> str:
    """Read the editor's previous-note shortcut from the add-on configuration.

    Returns:
        The configured shortcut, an empty string to disable it, or the default when it is missing or invalid.
    """
    return _resolve(config, "previous_note_shortcut", DEFAULT_PREVIOUS_NOTE_SHORTCUT)


def resolve_next_note_shortcut(config: object) -> str:
    """Read the editor's next-note shortcut from the add-on configuration.

    Returns:
        The configured shortcut, an empty string to disable it, or the default when it is missing or invalid.
    """
    return _resolve(config, "next_note_shortcut", DEFAULT_NEXT_NOTE_SHORTCUT)
