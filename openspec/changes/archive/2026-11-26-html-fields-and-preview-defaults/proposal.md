# Proposal

## Why

Showing some fields as Markdown and others as HTML makes editing inconsistent, and the Markdown conversion adds a dependency and rules about when a field counts as "lossless". Stored field HTML is usually a single long line, the field text is small, and the card preview takes most of the window when it opens. All of this makes the editor hard to read.

## What Changes

- **BREAKING**: Every field is edited as HTML. Markdown mode, the Markdown/HTML badge and the `markdown` runtime dependency are removed.
- Fields are shown with readable line breaks and indentation at block-level boundaries. Formatting is for display only: saving converts the field back to compact HTML, so the rendered card does not change. A field is shown exactly as stored when it cannot be formatted safely.
- Field editors highlight HTML syntax, including Anki cloze deletions and MathJax.
- Field text uses a monospace font at a larger default size that can be changed with a new `field_font_size` setting.
- The editor opens with the fields and the preview at equal widths.
- The preview shows the back of the selected card by default. The Front button stays available.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `note-editor`: Markdown mode is removed and fields are edited as HTML. Adds display-only formatting with compaction on save, syntax highlighting, a configurable field font size and an even initial split. The preview now defaults to a card's back.

## Impact

- `src/mindful/core`: remove `markdown_fields.py`; simplify `note_draft.py`; add HTML display formatting and compaction and field font size resolution.
- `src/mindful/application/card_preview.py`: change the default preview side to back.
- `src/mindful/ui/note_editor.py`: drop mode badges; add the syntax highlighter, font size and initial splitter sizes.
- `src/mindful/bootstrap.py` and `src/mindful/ui/browser_action.py`: pass the configured font size to the editor.
- `src/mindful/config.json` and `config.md`: add `field_font_size`.
- `pyproject.toml` and `uv.lock`: remove `markdown`. `scripts/build_addon.py`: update `ADDON_FILES`.
- `tests/core` and `tests/application`: replace Markdown tests and cover formatting, compaction, font size and the default side.
- `README.md`: describe HTML editing, formatting, the font size setting and preview defaults.
- No collection migration is needed. Previously saved Markdown-derived HTML is ordinary HTML.
