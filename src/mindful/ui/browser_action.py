"""Browser entry points that open the selected note in Mindful's editor."""

from collections.abc import Callable

from aqt import gui_hooks
from aqt.browser import Browser
from aqt.qt import QAction, QKeySequence, QMenu, qconnect

from ..application.card_preview import CardPreview
from ..application.note_editing import NoteEditing
from .note_editor import NoteEditorWindow

ACTION_TEXT = "Mindful: Edit Note..."
_ACTION_NAME = "mindfulEditNoteAction"


def _single_selected_note_id(browser: Browser) -> int | None:
    note_ids = set(browser.selected_notes())
    return int(next(iter(note_ids))) if len(note_ids) == 1 else None


def _action(browser: Browser) -> QAction | None:
    return browser.findChild(QAction, _ACTION_NAME)


class BrowserNoteAction:
    """Adds the edit action to Browser menus and opens a single editor window."""

    def __init__(self, editing: NoteEditing, preview: CardPreview, shortcut: Callable[[], str], field_font_size: Callable[[], int]) -> None:
        """Open notes through `editing` and `preview`, reading the shortcut for each new Browser and the font size for each new window."""
        self._editing = editing
        self._preview = preview
        self._shortcut = shortcut
        self._field_font_size = field_font_size
        self._window: NoteEditorWindow | None = None

    def register(self) -> None:
        """Register the Browser hooks."""
        gui_hooks.browser_menus_did_init.append(self._on_menus_did_init)
        gui_hooks.browser_will_show_context_menu.append(self._on_context_menu)
        gui_hooks.browser_did_change_row.append(self._update_enabled)

    def _on_menus_did_init(self, browser: Browser) -> None:
        action = QAction(ACTION_TEXT, browser)
        action.setObjectName(_ACTION_NAME)
        if shortcut := self._shortcut():
            action.setShortcut(QKeySequence(shortcut))
        qconnect(action.triggered, lambda: self._open(browser))
        qconnect(browser.form.menu_Notes.aboutToShow, lambda: self._update_enabled(browser))
        browser.form.menu_Notes.addSeparator()
        browser.form.menu_Notes.addAction(action)
        self._update_enabled(browser)

    def _on_context_menu(self, browser: Browser, menu: QMenu) -> None:
        action = _action(browser)
        if action is None:
            return
        self._update_enabled(browser)
        if action not in menu.actions():
            menu.addSeparator()
            menu.addAction(action)

    def _update_enabled(self, browser: Browser) -> None:
        if (action := _action(browser)) is not None:
            action.setEnabled(_single_selected_note_id(browser) is not None)

    def _open(self, browser: Browser) -> None:
        note_id = _single_selected_note_id(browser)
        if note_id is None:
            return
        if self._window is None or self._window.parentWidget() is not browser:
            window = NoteEditorWindow(browser, self._editing, self._preview, self._field_font_size())
            qconnect(window.destroyed, lambda: self._forget(window))
            self._window = window
        self._window.open_note(note_id)

    def _forget(self, window: NoteEditorWindow) -> None:
        if self._window is window:
            self._window = None
