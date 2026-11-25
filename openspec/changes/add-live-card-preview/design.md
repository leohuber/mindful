# Design

## Context

`NoteEditorWindow` edits a `NoteDraft` whose snapshot holds the original field HTML. `FieldDraft.to_html()` produces save-ready HTML, while `changed_html()` deliberately omits unchanged fields. The application and core layers cannot import Anki or Qt; the UI and integration layers are peers wired by `bootstrap`.

Anki's card-layout preview renders an uncommitted note, whereas its Browser previewer is a separate dialog that reloads the stored note. In the installed Anki version, `Note.ephemeral_card()` creates a default-deck card and runs `card_did_render`; Anki's legacy LaTeX hook on that path can write generated media. A live preview must not use a save-and-restore trick or inadvertently introduce those writes.

## Goals / Non-Goals

**Goals:**

- Render a draft through Anki's card-template machinery without persisting it.
- Keep the preview responsive and isolated from the editor's existing save and conflict handling.
- Preserve the host's card appearance and media behavior where a read-only preview can support them, and disclose limitations.

**Non-Goals:**

- Editing card templates, performing reviews, or predicting which conditional cards Anki will create on save.
- Guaranteeing identical output to a review session for card-specific state or arbitrary third-party rendering hooks.
- Introducing a separate HTML renderer or a new runtime dependency.

## Decisions

### One preview pane, multiple variants

Put a `QSplitter` around the existing fields scroll area and a right-hand preview pane. The pane has a card/variant selector and front/back controls. Initially select the first existing card in ordinal order, or the first available preview-only variant if no existing card is available, and show its front. Keep the selection and side during edits when possible.

For standard note types, list all templates and associate existing cards by ordinal. For cloze types, list the union of existing card ordinals and cloze numbers found in the transient draft using Anki's cloze-number API. Label an entry with no existing card as preview-only: it is not a prediction that Anki will generate a card. Recompute cloze entries on edits and refresh existing-card associations after a successful save. If a selected draft-only variant disappears, select the first remaining entry and its front, or show an empty state.

Showing one selected card scales better than rendering every card simultaneously, and including templates and draft clozes makes it possible to inspect new content before saving.

### Draft overlay and host boundary

Build an immutable sequence of preview field HTML from the draft: use each changed field's existing save conversion and the snapshot's original HTML for every unchanged field. This avoids changing markup that the editor considers equivalent but a card's CSS or JavaScript may distinguish.

Expose preview operations and plain request/result data through an Anki-independent application port, and inject its Anki-backed implementation through the composition root. Bind a preview session to the opened snapshot; obtain a separate in-memory Anki note and card/template metadata, verify the loaded note matches that snapshot, and overlay all preview fields on the transient note. Never call note/card update, flush, card generation, or undo operations for previewing. Refresh the session after a successful save; if the host note or template is unavailable or inconsistent, show a preview error without altering the draft.

This keeps `core` and `application` independent of host APIs and prevents external edits from being silently substituted for the draft. It also avoids making a stored note temporarily inconsistent while rendering.

### Read-only Anki rendering and display

Render the selected ordinary template or cloze ordinal against the transient note using Anki's uncommitted card-template rendering, with the regular question and answer templates and note-type CSS. Preserve the real card context where the host permits it; use an ephemeral context for preview-only variants. Use Anki's card-display webview resources for reviewer styling, collection media, MathJax, and clickable audio, rather than a generic Qt rich-text widget. Do not autoplay audio on edit refreshes.

Do not blindly call `Note.ephemeral_card()`: in the inspected host it invokes the media-generating `card_did_render` hook. The implementation can use the uncommitted `TemplateRenderContext` with an explicit regular template and `browser=True`, which in that host skips that hook while still rendering the supplied template and applying field filters. Verify the supported host version and side effects before relying on this path. If safe rendering is unavailable, or content such as uncached legacy LaTeX requires a collection write, show a clear unavailable/degraded status instead of writing to the collection or suppressing global hooks. Normal MathJax and existing media remain supported.

An ephemeral context can substitute default card metadata, and skipping write-capable rendering hooks can change output. Show a persistent, nonintrusive indication that card-specific context and add-on rendering may differ from review; do not silently claim exact review fidelity. Use Anki's existing webview trust and media handling, JSON-encode content passed to JavaScript, and expose only the bridge commands needed for preview interactions. Clean up the webview when the window closes.

Alternatives rejected: rendering fields independently would omit templates and clozes; rendering an existing card directly reloads persisted fields; temporarily saving the draft would violate collection safety.

### Debounced, current-only updates

Schedule an initial render when a draft opens and debounce field edits using a short single-shot Qt timer, as Anki's card-layout preview does. Card and side changes request an immediate update. Carry a generation token and note identity through any deferred rendering or webview callbacks; discard completions for superseded drafts, selections, or closed windows. Cancel pending work on note replacement and close. Keep UI updates on the main thread.

On failure, replace the card with an understandable error or empty state and retain the draft, current dirty state, and existing save controls. A later successful render replaces the status. This avoids stale previews and prevents expensive renders or audio playback on every keystroke.

## Risks / Trade-offs

- **Card-specific context or add-on hook differences** -> Preserve available context, label the preview's limitations, and compare representative cards with Anki's own preview during manual verification.
- **Legacy LaTeX or other render paths writing media** -> Use a verified read-only path; show unsupported content rather than modifying the collection.
- **Large or expensive templates** -> Debounce work, render only the selected variant, and ignore stale results.
- **Anki API or webview behavior changes** -> Keep host-specific logic behind the preview port and fail visibly without blocking editing.

## Migration Plan

No collection migration is needed. Include any new runtime modules or assets in the explicit add-on archive allowlist and document the preview and its limitations. Rolling back the add-on removes the pane without changing saved notes or scheduling.
