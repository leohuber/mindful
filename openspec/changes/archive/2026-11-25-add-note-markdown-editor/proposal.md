# Proposal

## Why

Mindful has an add-on foundation but no user-facing feature yet. Note fields are stored as HTML, which is awkward to read and edit as source and noisy for future AI-assisted editing. A Mindful note editor that presents fields as Markdown, while keeping the stored notes as standard Anki HTML, is the first useful feature and the surface that later AI edits will build on.

## What Changes

- Add a "Mindful: Edit Note..." action to the Anki Browser's Notes menu and table context menu. It is available only when exactly one note is selected, and it has a configurable keyboard shortcut (default `Ctrl+Shift+O`, shown as `Cmd+Shift+O` on macOS).
- Add a Mindful note editor window that shows every field of the selected note, labeled with its field name.
- Show each field as Markdown when it converts from HTML to Markdown and back without losing meaning. Otherwise show the field as raw HTML and indicate why.
- Preserve Anki-specific content during conversion: cloze deletions, sound tags, MathJax, and images.
- Save only the fields the user changed, as one undoable collection operation, after checking that the note was not changed elsewhere since it was opened.
- Ask before discarding unsaved edits. Never write to the collection without an explicit save.
- Add an add-on configuration file for the shortcut and include the new modules and configuration in the archive allowlist.
- Out of scope: AI-assisted editing, rendered preview or diff view, editing several notes at once, entry points other than the Browser, changing note types or templates, and storing Markdown in the collection.

## Capabilities

### New Capabilities

- `note-editor`: Opening a single note from the Browser in Mindful's editor, presenting its fields as Markdown or HTML without loss, and saving user edits safely back to the collection.

### Modified Capabilities

None. Loading and profile switching still leave collections unchanged. Only an explicit save in the new editor writes note data.

## Impact

- **Code:**
  - Host-independent HTML-to-Markdown conversion, fidelity checks, and edit-draft rules go in `core`.
  - The open and save use cases and a note-store interface go in `application`.
  - The collection adapter and undoable save operation go in `integration`.
  - The Browser action and editor window go in `ui`.
  - `bootstrap` wires these together.
- **Dependencies:** Uses the `markdown` (required by `anki`) and `beautifulsoup4` (required by `aqt`) packages supplied by Anki's runtime. They are declared for development but not bundled in the archive.
- **Packaging:** `scripts/build_addon.py` gains the new modules, `config.json`, and `config.md`.
- **Docs:** The README describes the editor, the shortcut, and Markdown/HTML field modes.
