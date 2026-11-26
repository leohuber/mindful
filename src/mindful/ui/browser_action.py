"""Browser entry points that open the selected note in Mindful's editor."""

from collections.abc import Callable

from aqt import gui_hooks
from aqt.browser import Browser
from aqt.qt import QAction, QKeySequence, QMenu, qconnect

from ..application.card_preview import CardPreview
from ..application.note_editing import NoteEditing
from .note_editor import NavigationDirection, NoteEditorWindow, NoteNavigation

ACTION_TEXT = "Mindful: Edit Note..."
_ACTION_NAME = "mindfulEditNoteAction"


def _single_selected_note_id(browser: Browser) -> int | None:
    note_ids = set(browser.selected_notes())
    return int(next(iter(note_ids))) if len(note_ids) == 1 else None


def _action(browser: Browser) -> QAction | None:
    return browser.findChild(QAction, _ACTION_NAME)


class BrowserNoteNavigator:
    """Moves a Browser's selection to the previous or next distinct note."""

    def __init__(self, browser: Browser) -> None:
        """Navigate the rows of `browser`."""
        self._browser = browser

    def can_move(self, direction: NavigationDirection) -> bool:
        """Whether the Browser has a row in `direction`.

        Returns:
            True if a row exists before or after the Browser's current row.
        """
        table = self._browser.table
        return table.has_previous() if direction == "previous" else table.has_next()

    def move(self, direction: NavigationDirection, on_moved: Callable[[int | None], None]) -> None:
        """Select the nearest row in `direction` whose note differs from the current one.

        Saves the Browser's own editor first, then calls `on_moved` with the selected note id, or with None
        after restoring the starting row when only rows of the current note remain.
        """
        editor = self._browser.editor
        if editor is None:
            self._step(direction, on_moved)
        else:
            editor.call_after_note_saved(lambda: self._step(direction, on_moved))

    def _step(self, direction: NavigationDirection, on_moved: Callable[[int | None], None]) -> None:
        table = self._browser.table
        forward, back = (table.to_previous_row, table.to_next_row) if direction == "previous" else (table.to_next_row, table.to_previous_row)
        start = _single_selected_note_id(self._browser)
        steps = 0
        # Bound the walk by the row count in case a step cannot move the cursor.
        while steps < table.len() and self.can_move(direction):
            forward()
            steps += 1
            note_id = _single_selected_note_id(self._browser)
            if note_id is not None and note_id != start:
                on_moved(note_id)
                return
        for _ in range(steps):
            back()
        on_moved(None)


class BrowserNoteAction:
    """Adds the edit action to Browser menus and opens a single editor window."""

    def __init__(
        self,
        editing: NoteEditing,
        preview: CardPreview,
        shortcut: Callable[[], str],
        field_font_size: Callable[[], int],
        navigation_shortcuts: Callable[[], tuple[str, str]],
    ) -> None:
        """Open notes through `editing` and `preview`.

        Reads the edit shortcut for each new Browser, and the font size and the previous and next note shortcuts
        for each new window.
        """
        self._editing = editing
        self._preview = preview
        self._shortcut = shortcut
        self._field_font_size = field_font_size
        self._navigation_shortcuts = navigation_shortcuts
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
        if self._window is not None and self._window.parentWidget() is browser:
            self._window.update_navigation()

    def _open(self, browser: Browser) -> None:
        note_id = _single_selected_note_id(browser)
        if note_id is None:
            return
        if self._window is None or self._window.parentWidget() is not browser:
            previous_shortcut, next_shortcut = self._navigation_shortcuts()
            navigation = NoteNavigation(BrowserNoteNavigator(browser), previous_shortcut, next_shortcut)
            window = NoteEditorWindow(browser, self._editing, self._preview, self._field_font_size(), navigation)
            qconnect(window.destroyed, lambda: self._forget(window))
            self._window = window
        self._window.open_note(note_id)

    def _forget(self, window: NoteEditorWindow) -> None:
        if self._window is window:
            self._window = None
