from collections.abc import Callable

import pytest

from mindful.core.shortcuts import (
    DEFAULT_EDIT_NOTE_SHORTCUT,
    DEFAULT_NEXT_NOTE_SHORTCUT,
    DEFAULT_PREVIOUS_NOTE_SHORTCUT,
    resolve_edit_note_shortcut,
    resolve_next_note_shortcut,
    resolve_previous_note_shortcut,
)


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (None, DEFAULT_EDIT_NOTE_SHORTCUT),
        ({}, DEFAULT_EDIT_NOTE_SHORTCUT),
        ({"edit_note_shortcut": "Ctrl+Shift+O"}, "Ctrl+Shift+O"),
        ({"edit_note_shortcut": " Alt+F5 "}, "Alt+F5"),
        ({"edit_note_shortcut": "Ctrl+Alt+E"}, "Ctrl+Alt+E"),
        ({"edit_note_shortcut": ""}, ""),
        ({"edit_note_shortcut": "   "}, ""),
        ({"edit_note_shortcut": "Ctrl+Banana"}, DEFAULT_EDIT_NOTE_SHORTCUT),
        ({"edit_note_shortcut": "Ctrl+Ctrl+O"}, DEFAULT_EDIT_NOTE_SHORTCUT),
        ({"edit_note_shortcut": "Hyper+O"}, DEFAULT_EDIT_NOTE_SHORTCUT),
        ({"edit_note_shortcut": 5}, DEFAULT_EDIT_NOTE_SHORTCUT),
    ],
)
def test_resolve_edit_note_shortcut(config: object, expected: str) -> None:
    assert resolve_edit_note_shortcut(config) == expected


@pytest.mark.parametrize(
    ("resolve", "key", "default"),
    [
        (resolve_previous_note_shortcut, "previous_note_shortcut", DEFAULT_PREVIOUS_NOTE_SHORTCUT),
        (resolve_next_note_shortcut, "next_note_shortcut", DEFAULT_NEXT_NOTE_SHORTCUT),
    ],
)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("Alt+PgDown", "Alt+PgDown"),
        (" Ctrl+N ", "Ctrl+N"),
        ("", ""),
        ("Ctrl+Banana", None),
        (3, None),
    ],
)
def test_resolve_navigation_shortcut(resolve: Callable[[object], str], key: str, default: str, value: object, expected: str | None) -> None:
    config = {} if value is None else {key: value}
    assert resolve(config) == (default if expected is None else expected)


def test_navigation_shortcuts_ignore_each_others_keys() -> None:
    config = {"previous_note_shortcut": "Alt+P", "next_note_shortcut": "Alt+N"}
    assert (resolve_previous_note_shortcut(config), resolve_next_note_shortcut(config)) == ("Alt+P", "Alt+N")
