# Design

## Context

See `proposal.md` for motivation and `specs/note-editor/spec.md` for required behavior. Mindful currently has only its add-on foundation:
- `bootstrap.initialize()` is a no-op.
- The `core`, `application`, `integration`, and `ui` packages are empty.
- `.importlinter` keeps `core` and `application` free of `anki`, `aqt`, and Qt.
- `ui` and `integration` are independent peers that only `bootstrap` composes.
- `scripts/build_addon.py` packages an explicit file allowlist.
- Tests are unit tests only, with no dependency on the Anki API.

Facts from the Anki 26.09.4 development environment:
- Note fields are HTML strings.
- `Note.mod` has one-second resolution.
- `Collection.update_note` returns `OpChanges`.
- `aqt.operations.CollectionOp` runs undoable mutations in the background and refreshes views.
- The Browser exposes `selected_notes()`, `form.menu_Notes`, `gui_hooks.browser_menus_did_init`, and `gui_hooks.browser_will_show_context_menu`.
- `Ctrl+Shift+O` is not used by the Browser.
- The runtime supplies `markdown` (an `anki` requirement) and `beautifulsoup4` (an `aqt` requirement).

## Goals / Non-Goals

**Goals:**
- Keep conversion, fidelity checks, and draft rules pure and unit-testable in `core`.
- Model an edit as a snapshot plus a draft so a later AI feature can propose drafts through the same save path.
- Make every collection write explicit, undoable, and protected against overwriting concurrent changes.

**Non-Goals:**
- Full CommonMark coverage or a general HTML-to-Markdown converter.
- A rendered preview, a diff view, syntax highlighting, or editing several notes at once.
- Editing tags, deck, or note type. Only field contents are editable.
- Bundling third-party libraries in the archive.

## Decisions

### Layering and composition

```text
ui/browser_action.py   QAction + hooks ----+                 +--- integration/note_store.py
ui/note_editor.py      editor window       |                 |    (Collection adapter,
        |                                  v                 v     CollectionOp save)
        +------------------> application/note_editing.py <---+
                             (open/save use cases, NoteStore port)
                                           |
                                           v
                             core/markdown_fields.py   core/note_draft.py
                             (HTML <-> Markdown, fidelity) (snapshot, draft, changes)
bootstrap.py: builds the store and passes the use cases to the ui hooks at startup
```

- `application` defines a small `NoteStore` protocol for loading a snapshot and saving changed fields with an expected snapshot. `integration` implements it. `ui` depends only on `application`, and `bootstrap` composes them. This satisfies the existing layer and peer contracts without new contracts.
- Hooks are registered in `bootstrap.initialize()`. Registration doesn't touch the collection. The collection is read only when the user triggers the action, which is always after a profile is open.

### Snapshot and draft model

- A `NoteSnapshot` holds the note ID, modification time, and an ordered tuple of (field name, stored HTML).
- On open, each field becomes a `FieldDraft` holding its mode (Markdown or HTML), the original editor text, and the current editor text.
- A field counts as changed only when its current editor text differs from its original editor text. Unchanged fields are never converted back, so their stored HTML is untouched.
- Saving produces a mapping of field index to new HTML, for changed fields only. Markdown-mode fields are converted to HTML; HTML-mode fields are written verbatim.
- A future AI feature can set draft text the same way the editor does, so save and conflict handling stay shared.

### Custom subset converter for HTML to Markdown

Write a small converter on `bs4` that supports an explicit subset of markup:
- Text, `b`/`strong`, `i`/`em`, `code`, `a[href]`, `img[src]`
- `ul`/`ol`/`li`
- `br`, plus `div` and `p` as line or paragraph breaks

It refuses any other element or attribute, such as `style`, `class`, `table`, `span`, `u`, or `font`. A refusal makes the field open in HTML mode.

- Alternative considered: bundling `markdownify`. It handles more markup, but converts unknown markup on a best-effort basis, which hides loss, and adds a bundled dependency. The explicit subset defines exactly what is safe.

### Markdown to HTML with the bundled `markdown` package

- Render with `markdown`'s `nl2br` and `sane_lists` extensions, then make the output look like Anki's editor output:
  - Unwrap a single outer `<p>`.
  - Join paragraphs with `<br><br>`.
  - Use `<b>` and `<i>`.
- Alternative considered: writing our own Markdown parser. Rejected, because `markdown` is already in the host and handles escaping and lists correctly.

### Protected Anki tokens

- Before Markdown rendering, swap these tokens for opaque placeholders and restore them afterwards:
  - MathJax: `\(...\)` and `\[...\]`
  - Sound tags: `[sound:...]`
- When converting HTML to Markdown, emit the same tokens literally, without escaping.
- This stops backslash escapes and emphasis rules from changing them. Cloze markers (`{{cN::...::...}}`) have no Markdown meaning, so they stay as literal text and their contents remain editable formatted text.
- Placeholders use characters that can't appear in field text (Unicode private-use code points), so they can't collide with user content.

### Fidelity check by canonical comparison

A field opens in Markdown mode only if both of these hold:
- The converter accepts it.
- `canonical(html) == canonical(md_to_html(html_to_md(html)))`

Here `canonical` parses the HTML with `bs4` and:
- maps `strong`→`b` and `em`→`i`,
- treats `div`/`p` boundaries and `br` as line breaks,
- collapses insignificant whitespace,
- decodes entities,
- then serializes the result.

The check runs once per field when the note opens and needs no I/O.

### Save with conflict detection in one undoable operation

- `integration` runs a `CollectionOp`. Inside it, it:
  1. reloads the note,
  2. raises a conflict error if the note is missing, or if its `mod` or any stored field differs from the snapshot,
  3. otherwise assigns the changed fields and returns `col.update_note(note)`.
- Comparing field contents as well as `mod` covers changes made within the same second.
- The op's success callback reports the saved snapshot. The failure callback distinguishes "changed elsewhere" from "deleted", and the editor keeps the draft.
- Undo and the Browser refresh come from `OpChanges`.

### Browser action and configuration

- One `QAction`, "Mindful: Edit Note...", is created per Browser in `browser_menus_did_init` and added to `form.menu_Notes`. The same action is added to the table context menu in `browser_will_show_context_menu`.
- Its enabled state is updated from the Browser selection, so it is enabled only when `selected_notes()` has length 1.
- The shortcut comes from `mw.addonManager.getConfig(__name__)["edit_note_shortcut"]`:
  - It defaults to `Ctrl+Shift+O`.
  - An empty value means no shortcut.
  - An invalid or missing value falls back to the default.
- `config.json` and `config.md` ship with the add-on. Changes apply to Browser windows opened afterwards.

### Editor window

- There is one non-modal Mindful editor window, parented to the Browser.
- It has one labeled `QPlainTextEdit` per field, with a mode badge reading "Markdown" or "HTML", and a tooltip explaining HTML mode.
- Save is enabled only when the draft has changes.
- Opening another note, closing the window, or closing the Browser while there are unsaved edits asks for confirmation to discard them.
- After a successful save, the window reloads the snapshot from the saved note.
- All UI work runs on the main thread.

## Risks / Trade-offs

- [Many real fields fall outside the subset, for example pasted `span`/`style` markup, so most open in HTML mode] → The read-only fidelity audit (tasks group 2) measures this against a copy of a real collection before the UI is built. The subset can then grow based on that data.
- [The canonical comparison treats two different HTML forms as equal and drops a meaningful difference] → Keep the equivalence rules minimal and listed explicitly. Unit-test each rule with pairs that should and should not be equal.
- [Saving rewrites a changed Markdown field in Anki-style HTML that differs from its original markup] → Only edited fields are rewritten, the rewrite is semantically equivalent to what the user typed, and the save can be undone.
- [`Ctrl+Shift+O` conflicts with another add-on] → The shortcut is configurable, and an empty value disables it.
- [The Browser's own editor has focus and handles the shortcut first] → Check this in the manual Anki smoke test. The menu and context-menu entries remain available either way.
- [`markdown` or `bs4` behavior changes in a future Anki release] → The unit tests run against the pinned development versions and pin the expected HTML output, so a change in behavior shows up as a test failure.

### Fidelity audit (2026-11-25)

The read-only audit of a standalone collection copy found 15,689 Markdown-mode fields and 3,717 HTML-mode fields (19,406 total):

| Note type | Markdown | HTML |
| --- | ---: | ---: |
| Basic | 41 | 34 |
| CodePython | 2,551 | 3,665 |
| LangENWord | 15 | 0 |
| LangFRAdjective | 1,206 | 0 |
| LangFRExpression | 600 | 0 |
| LangFRNoun | 9,304 | 0 |
| LangFRVerbNonConj | 1,600 | 0 |
| Math | 372 | 18 |

The most frequent HTML fallbacks were attributes on `code` (2,725 fields), `pre` elements (938), attributes on `div` (32), and attributes on `img` (18). Two fields had unsupported list content and two failed the round-trip comparison. Code-related markup accounts for 3,663 of the 3,717 fallbacks. Decision: keep the planned subset for this change. These fields open in HTML mode, which the spec allows and which is lossless. Supporting attributed `code` and `pre` blocks can be proposed as a follow-up change.

Ruff's `TID252` rule (no parent-relative imports) is disabled in `pyproject.toml`, because `application`, `integration`, `ui` and `bootstrap` must use relative imports such as `..core` so that numeric AnkiWeb add-on directory names work.

## Migration Plan

There's no data migration: notes stay in standard Anki HTML, and Mindful stores nothing persistent apart from its add-on configuration. To roll back, disable or remove the add-on. Saved edits stay as normal note changes that can be undone during the session.
