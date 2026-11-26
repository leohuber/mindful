# Design

## Context

See proposal.md for motivation and `specs/note-editor/spec.md` for the required behavior.

Today `FieldDraft` holds a per-field `mode`. `to_html()` runs Markdown fields through `core/markdown_fields.py` and returns HTML fields as typed. A field counts as changed when its editor text differs from the text it opened with, and `NoteDraft.preview_html()` combines the converted changed fields with the snapshot's original HTML. `NoteEditorWindow` builds one `QPlainTextEdit` per field. Only HTML fields get the system monospace font, and no font size is set. The window's `QSplitter` has 1:1 stretch factors, but the initial widths follow size hints, so the web preview starts wide. `PreviewSelection` resets the side to `"front"` on first load, on another card selection and on fallback. The configuration is read in `bootstrap.py`, which passes a shortcut provider to `BrowserNoteAction`. `core` and `application` must stay independent of Anki and Qt.

## Goals / Non-Goals

**Goals:**

- One editing path for every field: displayed HTML text in, compact stored HTML out.
- Display formatting that cannot change how the card renders, and that does nothing when that cannot be guaranteed.
- No new runtime dependency.

**Non-Goals:**

- Visual (WYSIWYG) editing, auto-closing tags or other CodeMirror-style editing features.
- Reformatting HTML that is stored in the collection without an edit.
- Remembering the splitter position or the selected side between sessions.

## Decisions

### Display formatting is a reversible, verified transform in `core`

Add a pure `core` module with `format_html(html) -> str | None` and `compact_html(text) -> str`.

- **Tokenizing.** Split the source into tags, comments and text runs by slicing the original string, so every token's characters are preserved verbatim. Do not re-serialize through a parser, which would normalize quotes, case and entities.
- **Formatting.** Insert a newline and two-space indentation per nesting level only at a boundary where the original has no whitespace and at least one side is a block-level tag (`address`, `article`, `aside`, `blockquote`, `details`, `dd`, `div`, `dl`, `dt`, `figcaption`, `figure`, `footer`, `h1`–`h6`, `header`, `hr`, `li`, `main`, `nav`, `ol`, `p`, `section`, `table`, `tbody`, `td`, `tfoot`, `th`, `thead`, `tr`, `ul`), or directly after `<br>`. Never insert inside `pre`, `textarea`, `script`, `style` or `code`. Never insert inside a text run, so cloze, MathJax and sound tags are untouched.
- **Compacting.** Remove whitespace runs that contain a newline and sit at the same kind of boundary, outside the protected elements.
- **Verification.** `format_html` returns `None` unless `compact_html(formatted) == html`. Such fields are shown exactly as stored: fields that already contain whitespace at those boundaries, unbalanced or unusual markup, and fields over a size limit.

Alternatives: `html.parser` re-serialization and BeautifulSoup `prettify()` both change the stored markup and break the round trip. BeautifulSoup would also add a dependency. Formatting at every tag would insert visible spaces between inline elements.

### The draft owns the display/storage mapping

`FieldDraft` loses `mode` and `reason` and gains `formatted: bool`. `NoteDraft.from_snapshot` sets `text = original_text = format_html(html) or html`. `to_html()` returns `compact_html(text)` for formatted fields and `text` verbatim otherwise. A field is changed only when `text != original_text`, as today, so opening and closing never writes. `changed_html()` and `preview_html()` keep their contracts, so save, conflict detection and preview pick up compaction automatically.

Alternative: compare `to_html()` with the stored HTML to detect changes. That would ignore whitespace-only edits, but for unformatted fields it would treat existing boundary whitespace as a change. The existing text comparison is simpler and already specified.

### Remove the Markdown path

Delete `core/markdown_fields.py` and its tests. Remove its `ADDON_FILES` entry, the `markdown` dependency and the lock entry (`uv remove markdown`). Remove the badge, its tooltips and the per-mode font branch from the editor.

### Syntax highlighting with `QSyntaxHighlighter`

A `ui` highlighter is attached to each field's document. Regex rules cover tags, attribute names, quoted attribute values, comments, entities, cloze `{{cN::...}}` and MathJax delimiters `\( \) \[ \]`. Multi-line comments use block state. Colors come from the editor's palette, chosen by Anki's `theme_manager.night_mode`, so both themes stay readable. The highlighter only changes how text looks, never the text itself.

Alternative: a CodeMirror webview per field. It offers more features but needs a bundled JS asset and a text bridge, and is deferred.

### Font size from configuration, resolved in `core`

Add `resolve_field_font_size(config) -> int` next to the shortcut resolver. It returns an `int` between 8 and 48, otherwise 14, and rejects `bool`. `bootstrap` passes a provider to `BrowserNoteAction`, which passes the size to `NoteEditorWindow` when it creates the window. Every editor uses `QFontDatabase.systemFont(FixedFont)` with that point size. Add `"field_font_size": 14` to `config.json` and document it in `config.md`.

### Equal split and back-side default

After the window geometry is restored, set the splitter sizes to two equal halves of its width. Do this once, when the window is first shown, so a restored window size is respected. In `PreviewSelection`, make `"back"` the initial side and the side after another card is selected or after a fallback. The Front and Back buttons stay as they are.

## Risks / Trade-offs

- [Card CSS with `white-space: pre*` on a block container makes newlines between blocks visible] -> Formatting is display-only, and compaction removes only the newline whitespace the formatter adds at block boundaries. A newline the user deliberately types at such a boundary in a formatted field is removed on save; this is documented.
- [Unusual markup confuses the tokenizer] -> The round-trip check falls back to showing the field exactly as stored, and tests cover malformed and attribute-heavy input.
- [Highlighting cost on large fields] -> Highlighting is per block and incremental, and fields are small in practice.
- [Removing Markdown is breaking for users who liked it] -> Saved notes are unaffected because they were always stored as HTML. The README explains the change.

## Migration Plan

No collection migration. Release with the updated README and `config.md`. Anki merges the new `field_font_size` default into existing user configuration. Rolling back restores Markdown mode without affecting stored notes.
