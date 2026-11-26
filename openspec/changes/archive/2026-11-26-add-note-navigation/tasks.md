# Tasks

## 1. Shortcut configuration

- [x] 1.1 In `src/mindful/core/shortcuts.py`, factor the existing resolution into a shared `_resolve(config, key, default)` and add `resolve_previous_note_shortcut` and `resolve_next_note_shortcut`, defaulting to `Ctrl+Alt+Left` and `Ctrl+Alt+Right`. Verify that `uv run pytest tests/core/shortcuts_test.py` passes with new cases for both keys: missing, valid, padded, empty and invalid values.
- [x] 1.2 Add `previous_note_shortcut` and `next_note_shortcut` to `src/mindful/config.json` and document them in `src/mindful/config.md`. Verify that the JSON parses and that each key's description in `config.md` matches its default.

## 2. Browser navigator

- [x] 2.1 In `src/mindful/ui/browser_action.py`, implement a Browser-bound navigator with `can_move(direction)` and `move(direction, on_moved)`. It saves the Browser's built-in editor first, steps rows until a different note is selected, and restores the starting row with a "no other note" tooltip when none is found. Verify that `uv run pyrefly check` passes.
- [x] 2.2 Pass the navigator and the resolved navigation shortcuts to `NoteEditorWindow` on creation, and refresh the window's navigation state from the existing `browser_did_change_row` hook. Update `src/mindful/bootstrap.py` to supply the new shortcut resolvers. Verify that `uv run lint-imports` and `uv run pyrefly check` pass.

## 3. Editor controls

- [x] 3.1 In `src/mindful/ui/note_editor.py`, split the loading part of `open_note` into a helper that loads a note without asking, and keep `open_note`'s behavior unchanged. Verify that the full test suite passes.
- [x] 3.2 Add "< Previous" and "Next >" buttons to the left of the bottom button row, plus window-scoped `QShortcut`s for the configured shortcuts, with the shortcuts in the button tooltips. Implement the flow: no navigation while saving, `confirm_discard`, `navigator.move`, then load. Enable or disable the buttons from `can_move`. Verify that `uv run pyrefly check` and `uv run ruff check src/mindful tests scripts` pass.
- [x] 3.3 Update `README.md` to describe the navigation buttons, the default shortcuts and the two configuration keys. Verify that the documented defaults match `config.json`.

## 4. Integration check

- [x] 4.1 Run the project quality gate (pytest, Ruff lint and format check, Pyrefly, import-linter) with the `mindful_check_code_quality` skill and verify that all checks pass.
- [x] 4.2 In Anki (`uv run mindful`), manually verify the spec scenarios:
  - Next and previous move the editor and the Browser selection in notes mode.
  - In card mode, rows of the same note are skipped.
  - The buttons are disabled on the first and last rows.
  - Cancelling the discard prompt keeps the edits and the Browser selection.
  - `Cmd+Option+Left/Right` work while a field has focus, and plain arrow keys move the cursor.
  - A custom value and an empty value for `next_note_shortcut` take effect in a new editor window.
