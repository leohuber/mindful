import pytest

from mindful.core.shortcuts import DEFAULT_EDIT_NOTE_SHORTCUT, resolve_edit_note_shortcut


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
