# Design

## Context

`BrowserNoteAction` (in `ui/browser_action.py`) owns at most one `NoteEditorWindow` for each Browser. It opens the note selected in the Browser with `open_note(note_id)`. `open_note` asks before discarding unsaved edits and then loads the note. The editor has no link back to the Browser's table.

Anki's Browser table can move its current row with `to_previous_row()` and `to_next_row()` and reports `has_previous()` and `has_next()`. After a move, `get_selected_note_ids()` gives the note of the new row, and the move fires `browser_did_change_row`, which the add-on already listens to. Anki's own previous/next actions first call `browser.editor.call_after_note_saved(...)` so that edits in the Browser's built-in editor are saved before the row changes.

Reading the note on a row without moving to it is only possible through the table's private model.

## Goals / Non-Goals

**Goals:**
- Navigation works only through Anki's public Browser table API.
- The editor does not depend on Browser internals. The Browser-specific logic stays in `browser_action.py`.
- Moving reuses the existing discard confirmation and never writes to the collection.

**Non-Goals:**
- The editor does not follow every Browser selection change automatically. It changes notes only through the edit action or the new navigation controls.
- No first-note or last-note controls, and no wrapping around at the ends.
- No automated UI tests. The `ui` layer has no test harness today.

## Decisions

### The Browser decides where to move; the editor asks for it
`NoteEditorWindow` gets a small navigator interface (a `Protocol` in the ui module) with `can_move(direction)` and `move(direction, on_moved)`. `BrowserNoteAction` provides it, bound to the owning Browser.
- **Why:** the editor stays testable and unaware of Browser internals, and the existing parent and ownership relationship stays unchanged.
- **Alternative:** have the editor call `parentWidget().table` directly. Rejected because it couples the editor to `Browser`.

### Step through rows until the note changes
`move` first calls `browser.editor.call_after_note_saved` when the Browser has its own editor. It then calls `to_next_row()` or `to_previous_row()` repeatedly while `has_next()` or `has_previous()` is true, until the single selected note differs from the starting one.
- If no different note is found, it returns to the starting row by stepping back the same number of rows and reports that there is no other note.
- `can_move` is `has_previous()` or `has_next()`.
- **Why:** this uses only public API.
- **Alternative:** read row note ids from `table._model`. That would let the buttons be disabled precisely in card mode, but it uses private API. The spec instead accepts a notice for that rare case.

### Navigation starts from the Browser's current row
Movement is relative to the Browser's current row, not to the row of the note shown in the editor. These are the same unless the user changed the Browser selection after opening the note. In that case, moving starts from what the Browser shows, which matches the "Browser is the source of truth" model.

### Confirm first, then move, then load without asking again
The editor flow is:
1. Return if a save is in progress.
2. Call `confirm_discard()`. If the user cancels, stop before touching the Browser.
3. Call `navigator.move(direction, on_moved)`.
4. In `on_moved(note_id)`, load the note through the loading part of `open_note`, refactored into a helper that does not ask again.

Asking before moving the Browser means that cancelling leaves both the editor and the Browser unchanged.

### Button state follows the Browser row
The `browser_did_change_row` hook already in `BrowserNoteAction` also tells the open window to refresh its navigation buttons. The window also refreshes them after each note load.

### Shortcuts are window-scoped `QShortcut`s and configurable
- Two `QShortcut`s with `Qt.ShortcutContext.WindowShortcut` trigger the same handlers as the buttons. The buttons' tooltips show the shortcuts.
- `Ctrl+Alt+Left/Right` (`Cmd+Option` on macOS) are not standard text-editing keys, so `QPlainTextEdit` does not consume them and they work while a field has focus.
- Resolution generalizes `core/shortcuts.py`: a shared `_resolve(config, key, default)` backs `resolve_edit_note_shortcut`, plus new `resolve_previous_note_shortcut` and `resolve_next_note_shortcut`.
- `bootstrap.py` passes the two new resolvers to `BrowserNoteAction`, which reads them when it creates each window.
- **Alternatives:** plain arrow keys would break text editing. Fixed shortcuts would leave users stuck where the desktop already uses `Ctrl+Alt+Arrow`, for example GNOME's workspace switching.

### Button placement
The bottom button row gets "< Previous" and "Next >" on the left, with Save and Close on the right. This keeps the preview controls unchanged.

## Risks / Trade-offs

- **Card mode with many rows of one note:** each row step fires `browser_did_change_row` and reloads the Browser's built-in editor. This is acceptable because notes rarely have many cards. → Stop as soon as the note changes.
- **No other note in card mode:** in that rare case the button is enabled but does nothing except show a notice. → Show a tooltip, as the spec requires.
- **Desktop shortcut conflicts:** some systems already use `Ctrl+Alt+Arrow`. → The shortcuts are configurable and can be turned off.
- **Selection changed while the confirmation is open:** the dialog is modal, so the Browser cannot change underneath it.
- **Browser's built-in editor has pending edits:** `call_after_note_saved` saves them before the row changes, matching Anki's own navigation.
