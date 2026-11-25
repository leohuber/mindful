# Tasks

## 1. Draft and preview state

- [x] 1.1 Build the preview's immutable field HTML from changed-field save conversions and exact unchanged snapshot HTML; add unit tests for Markdown edits, raw HTML edits, unchanged markup, and edit-then-revert.
- [x] 1.2 Define an Anki-independent preview port and selection state for card ordinals, sides, and preview-only variants; use unit tests with pure-Python doubles to verify selection retention, fallback, and empty states.

## 2. Read-only Anki rendering

- [x] 2.1 Implement and wire a preview session that loads a separate note and card/template metadata, checks the opened snapshot, overlays draft fields, and reports missing or inconsistent host data; verify error handling and no save calls with unit-test doubles.
- [x] 2.2 Render uncommitted regular and cloze templates through a verified read-only Anki path; in a disposable profile check that rendering does not change notes, cards, scheduling, undo history, or collection media, including when uncached legacy LaTeX is present.
- [x] 2.3 Discover ordinary templates and the union of existing and draft cloze card ordinals, marking nonexistent cards preview-only; verify variant ordering and transitions with unit tests and a disposable-profile host check.
- [x] 2.4 Add any new runtime modules or assets to `scripts/build_addon.py`'s allowlist and verify the resulting archive contains them without development or user data.

## 3. Editor preview

- [x] 3.1 Add the resizable right-hand pane, card selector, and front/back controls; verify in Anki that existing fields remain editable and every existing card and available variant can be selected.
- [x] 3.2 Refresh from the draft on open, edits, selection changes, and successful save; debounce edits, preserve valid selections, and discard stale or post-close results. Verify rapid edits, note switches, save, and close with unit-test doubles.
- [x] 3.3 Display card CSS, clozes, collection images, MathJax, and clickable sound using Anki's webview resources; verify in a disposable profile that both sides render and editing does not restart audio.
- [x] 3.4 Show context limitations and recoverable error or empty states, clean up preview resources, and preserve the existing dirty, discard, conflict, and save behavior; verify failure and recovery with unit-test doubles and a manual editor check.
- [x] 3.5 Document the preview controls, preview-only variants, unsaved behavior, and rendering limitations in `README.md`; verify the instructions match the delivered UI.

## 4. End-to-end verification

- [x] 4.1 In a disposable Anki profile, compare representative standard and cloze card fronts and backs with Anki's preview, exercise multiple cards and unsaved variants, and confirm previewing leaves collection and media data unchanged while explicit save and undo still work.
- [x] 4.2 Run the `mindful_check_code_quality` skill and resolve any failures, covering the full pytest suite, Ruff lint and formatting, Pyrefly, and import-linter.
