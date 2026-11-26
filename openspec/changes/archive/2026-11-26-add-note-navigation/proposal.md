# Proposal

## Why

To edit several notes in a row, users must go back to the Browser, select the next note and run the edit action again for each note. Moving to the previous or next note from inside Mindful's editor, by button or keyboard, makes going through a list of notes much faster.

## What Changes

- Add "previous note" and "next note" buttons to Mindful's editor. They open the note before or after the current one in the Browser list, in the Browser's current search and sort order.
- Moving also moves the Browser's selection, so the Browser and the editor stay in sync.
- In card mode, rows that belong to the same note are skipped, so each step reaches a different note.
- The buttons are disabled when the Browser has no row in that direction. In card mode, if only cards of the current note remain in that direction, the user is told there is no other note.
- Add keyboard shortcuts that default to `Ctrl+Alt+Left` and `Ctrl+Alt+Right` (`Cmd+Option+Left` / `Cmd+Option+Right` on macOS). They work while a field has focus. Plain Left and Right keep moving the text cursor inside fields, so they cannot be used to move between notes.
- The shortcuts can be changed or turned off through the new configuration keys `previous_note_shortcut` and `next_note_shortcut`. Invalid values fall back to the defaults, as `edit_note_shortcut` does.
- Moving with unsaved edits asks before discarding them, as opening another note does today. Mindful never saves without an explicit save.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `note-editor`: adds requirements for moving to the previous or next note from the editor and for the configurable shortcuts that do this.

## Impact

- `src/mindful/ui/note_editor.py`: adds the navigation buttons and shortcuts and the confirm-then-move flow.
- `src/mindful/ui/browser_action.py`: moves the Browser's selection to the previous or next distinct note and reports whether each direction is available.
- `src/mindful/core/shortcuts.py`: generalizes shortcut resolution to the two new keys.
- `src/mindful/bootstrap.py`: passes the resolved navigation shortcuts to the UI.
- `src/mindful/config.json`, `src/mindful/config.md`, `README.md`: document the new defaults and configuration keys.
- `tests/core/shortcuts_test.py`: covers resolving the new keys.
- No new dependencies and no changes to the collection or data model.
