# Proposal

## Why

Mindful's editor shows field source but not how a note's cards will look in Anki. Users must save or leave the editor to inspect the rendered result, interrupting editing and making mistakes harder to catch.

## What Changes

- Add a resizable card-preview pane to the right of the note fields. Show one card at a time, with controls for its front and back and for selecting other cards or preview variants.
- Refresh the preview from the current, unsaved draft as fields are edited, using the same HTML that saving those fields would produce.
- Offer existing cards and draft-only template or cloze variants; identify variants that are not existing cards rather than implying they have been created.
- Use Anki's card-template preview rendering, styling, and media facilities, and report preview failures without losing edits. Disclose where a transient preview cannot represent a real card's context.
- Preserve the existing explicit-save, conflict-detection, undo, and discard behavior. Previewing must not create or update notes or cards.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `note-editor`: Add a live, draft-backed Anki card preview alongside the field editor.

## Impact

The note draft, editor UI, application boundary, and Anki integration will need preview support. The add-on archive allowlist must include any new runtime modules or assets. Documentation and unit tests need updates; card-template editing, review scheduling, and new third-party dependencies are out of scope.
