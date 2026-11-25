# Tasks

## 1. Dependencies

- [x] 1.1 Declare `markdown` and `beautifulsoup4` as project dependencies in `pyproject.toml`, with versions compatible with those Anki 26.09.4 supplies, and verify that `uv lock --check` passes and that `uv run python -c "import markdown, bs4"` succeeds

## 2. Core: HTML and Markdown conversion

- [x] 2.1 Implement the subset HTML-to-Markdown converter in `src/mindful/core/markdown_fields.py`. It supports text, `b`/`strong`, `i`/`em`, `code`, `a[href]`, `img[src]`, lists, `br`, and `div`/`p` breaks, and rejects anything else. Verify with table-driven tests in `tests/core/markdown_fields_test.py` covering each supported element and rejections of `span`, `style`, `table`, and `u`.
- [x] 2.2 Implement Markdown-to-HTML rendering with `markdown` (`nl2br`, `sane_lists`) and normalize the output to Anki-style HTML (unwrap a single `<p>`, join paragraphs with `<br><br>`, use `<b>`/`<i>`). Verify with tests that assert the exact HTML for paragraphs, line breaks, lists, links, and images.
- [x] 2.3 Protect MathJax `\(...\)`/`\[...\]` and `[sound:...]` tokens with placeholders in both directions, and keep cloze markers as literal text. Verify with tests showing that `\(x_1^2\)`, `[sound:clip_one.mp3]`, and `{{c1::answer::hint}}` round-trip unchanged, including when they sit next to emphasis.
- [x] 2.4 Implement the canonical HTML comparison and the per-field mode decision (Markdown when the converter accepts the field and the round trip is equivalent, HTML otherwise). Verify with tests for pairs that should compare equal (`strong`/`b`, `div`/`br` breaks, whitespace) and pairs that should not (different text, links, or images), plus the empty-field case.

## 3. Fidelity audit against real data

- [x] 3.1 Add `scripts/audit_markdown_fidelity.py`. It opens a copy of a collection file given as an argument, never the live profile, and reports per note type how many fields would open in Markdown mode and the most common rejection reasons. It uses the core converter and writes nothing. Verify it with Ruff and by running it on a copied collection and inspecting the report.
- [x] 3.2 Run the audit on a copy of the user's collection and record the results in this change's `design.md` under Risks / Trade-offs. If common markup outside the subset dominates, agree any subset additions with the user before continuing.

## 4. Core: snapshot and draft model

- [x] 4.1 Implement `NoteSnapshot` and `NoteDraft` in `src/mindful/core/note_draft.py`, covering field order, per-field mode, original and current editor text, changed detection, and building the changed-field HTML mapping (Markdown fields converted, HTML fields verbatim). Verify with `tests/core/note_draft_test.py`: no edits produce no changes, an edit to one field changes only that index, an edited HTML-mode field is saved verbatim, and editing then reverting a field counts as unchanged.

## 5. Application: use cases and port

- [x] 5.1 Define the `NoteStore` protocol and conflict errors (changed elsewhere, deleted), and implement the open and save use cases in `src/mindful/application/note_editing.py`. Verify with `tests/application/note_editing_test.py` using an in-memory fake store: opening builds a draft, saving sends only changed fields with the expected snapshot, conflicts and deletions surface as distinct errors, and saving a draft with no changes is rejected.

## 6. Integration: collection adapter

- [x] 6.1 Implement the collection-backed `NoteStore` in `src/mindful/integration/note_store.py`. It loads the snapshot from `Collection.get_note`, and saves through a `CollectionOp` that reloads the note, checks it is unchanged (`mod` and field contents) and still exists, assigns the changed fields, and returns `update_note` changes. Verify with `uv run lint-imports` and `uv run pyrefly check`. Behavior is checked in the manual smoke test (8.3).

## 7. UI: Browser action and editor window

- [x] 7.1 Add `config.json` (`{"edit_note_shortcut": "Ctrl+Shift+O"}`) and `config.md` to `src/mindful/`, and implement shortcut resolution (default, empty means none, invalid falls back to the default) as a pure function in `core`. Verify with unit tests for each case.
- [x] 7.2 Implement `src/mindful/ui/browser_action.py`. It adds the "Mindful: Edit Note..." action, with the configured shortcut, to `form.menu_Notes` through `browser_menus_did_init` and to the table context menu through `browser_will_show_context_menu`. The action is enabled only when exactly one note is selected and opens the editor through the injected use case. Verify with `uv run lint-imports` and `uv run pyrefly check`, and later in the smoke test.
- [x] 7.3 Implement `src/mindful/ui/note_editor.py`. It is a single non-modal window with one labeled `QPlainTextEdit` per field, a Markdown/HTML mode badge with a tooltip for HTML mode, Save enabled only when there are changes, confirmation before discarding unsaved edits (on close, on opening another note, and when the Browser closes), and messages for conflict and deletion that keep the draft. Verify with `uv run pyrefly check`, and later in the smoke test.

## 8. Wiring, packaging, and verification

- [x] 8.1 Wire the store, use cases, and Browser hooks in `bootstrap.initialize()` without touching the collection at startup. Add every new module plus `config.json` and `config.md` to `ADDON_FILES` in `scripts/build_addon.py`. Verify that the built `dist/mindful.ankiaddon` lists them and still excludes tests and caches.
- [x] 8.2 Document the editor in `README.md`: how to open it, the shortcut and how to change it, Markdown versus HTML field modes, preserved Anki content, and undo. Verify that the documented steps match the smoke-test behavior.
- [ ] 8.3 Manually smoke-test the built archive in Anki Desktop 26.09.4 with a disposable profile. Cover each spec scenario: menu, context-menu, and shortcut entry points; disabled states; Markdown and HTML fields; cloze, MathJax, sound, and image preservation; changed-fields-only save; undo; Browser refresh; conflict after editing in Anki's own editor; deleted note; and discard prompts. Also check that the shortcut works while the Browser's own editor has focus. Record the results.
- [x] 8.4 Run the `mindful_check_code_quality` skill (pytest, Ruff lint and format, Pyrefly, import-linter) and verify that every gate passes.

## Workflow follow-up

- Archive the change after review, which syncs `note-editor` into `openspec/specs/`.
