# Tasks

## 1. HTML display formatting in core

- [x] 1.1 Add a pure `core` module with `format_html` and `compact_html` as described in design.md. Verify with new `tests/core` cases: block and list markup is formatted and indented; inline runs, `<pre>`, cloze, MathJax and sound are untouched; `compact_html(format_html(x)) == x`; `None` is returned for input that cannot round-trip, such as existing boundary whitespace or malformed tags
- [x] 1.2 Replace `FieldDraft.mode`/`reason` with `formatted`. Open fields with formatted text when it is safe, and make `to_html()` compact formatted fields and return other fields verbatim. Verify with updated `tests/core/note_draft_test.py` cases: no edits produce no changes; an edited formatted field saves as compact HTML; a field shown as stored saves verbatim; reverting an edit counts as unchanged; `preview_html()` uses the compact form
- [x] 1.3 Delete `core/markdown_fields.py` and `tests/core/markdown_fields_test.py`, remove its `ADDON_FILES` entry in `scripts/build_addon.py`, and run `uv remove markdown`. Verify that `markdown` no longer appears in `src/mindful`, `pyproject.toml` or `uv.lock`, and that `uv run python scripts/build_addon.py` succeeds

## 2. Field font size configuration

- [x] 2.1 Add `resolve_field_font_size` to `core`: an `int` from 8 to 48, otherwise 14, and `bool` rejected. Verify with `tests/core` cases for the default, a valid value, out-of-range, non-number and `bool`
- [x] 2.2 Add `"field_font_size": 14` to `src/mindful/config.json` and document it in `src/mindful/config.md`. Pass the resolved size from `bootstrap.py` through `BrowserNoteAction` to `NoteEditorWindow`. Verify that `uv run lint-imports` passes and that a new editor window uses the configured size

## 3. Preview defaults

- [x] 3.1 Make `"back"` the initial side in `PreviewSelection`, and the side after another card is selected or after a fallback. Verify with updated `tests/application/card_preview_test.py` cases for the initial selection, another card selected, fallback, and a side kept through edits and saves
- [x] 3.2 Set equal splitter sizes once, when `NoteEditorWindow` is first shown, after the geometry is restored. Verify manually in Anki that the fields and preview open at equal widths and that dragging the divider still works

## 4. Editor UI

- [x] 4.1 Remove the Markdown/HTML badge, its tooltips and the per-mode font branch from `ui/note_editor.py`, and apply the monospace font at the configured size to every field. Verify manually that no badge is shown and every field uses the same font
- [x] 4.2 Add a theme-aware `QSyntaxHighlighter` for tags, attribute names and values, comments, entities, cloze deletions and MathJax delimiters, attached to each field editor. Verify manually in light and dark mode that `<span class="hint">{{c1::cell}}</span>` shows distinct styles and that typing does not change the text
- [x] 4.3 Update the module and class docstrings that mention Markdown. Verify that `grep -ri markdown src/mindful` returns nothing

## 5. Documentation and integration

- [x] 5.1 Update `README.md`: HTML editing, readable formatting and compaction on save (including the deliberate-newline caveat), syntax highlighting, `field_font_size`, the equal split and the back-side default. Verify that the README no longer mentions Markdown mode
- [x] 5.2 Update the Purpose of `openspec/specs/note-editor/spec.md` to describe HTML editing instead of Markdown. Verify with `openspec validate --specs`
- [x] 5.3 Run the `mindful_check_code_quality` skill (pytest, Ruff, Pyrefly, import-linter), then open a note in Anki with block, inline, cloze and MathJax content. Verify that the checks pass, opening and closing without edits writes nothing, and an edited formatted field saves compact HTML with an unchanged rendered card

## Workflow follow-up

- Archive the change after review, and verify that the merged `note-editor` spec has no Markdown requirements.
