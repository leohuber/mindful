# note-editor Specification

## Purpose

Lets users open a single Anki note in Mindful's editor, edit its fields as Markdown where this is lossless or as HTML otherwise, and save those edits safely back to the collection.

## Requirements

### Requirement: Open a note from the Browser

Mindful SHALL offer an "Edit Note" action in the Anki Browser's Notes menu and table context menu that opens the selected note in Mindful's editor.

#### Scenario: Open from the Notes menu
- **GIVEN** exactly one note is selected in the Browser
- **WHEN** the user chooses the Mindful edit action from the Notes menu
- **THEN** Mindful's editor opens showing that note

#### Scenario: Open from the context menu
- **GIVEN** exactly one note is selected in the Browser
- **WHEN** the user right-clicks the table and chooses the Mindful edit action
- **THEN** Mindful's editor opens showing that note

#### Scenario: Several cards of one note are selected
- **GIVEN** the Browser is in card mode and the selected cards all belong to one note
- **WHEN** the user chooses the Mindful edit action
- **THEN** Mindful's editor opens showing that note

### Requirement: Edit action requires exactly one note

The edit action SHALL be unavailable unless the Browser selection resolves to exactly one note.

#### Scenario: No selection
- **GIVEN** no rows are selected in the Browser
- **WHEN** the user opens the Notes menu or presses the shortcut
- **THEN** the action is disabled and no editor opens

#### Scenario: Several notes selected
- **GIVEN** rows belonging to two or more notes are selected
- **WHEN** the user opens the Notes menu or presses the shortcut
- **THEN** the action is disabled and no editor opens

### Requirement: Configurable keyboard shortcut

The edit action SHALL have a keyboard shortcut read from the add-on configuration, defaulting to `Ctrl+Shift+O`, which Qt shows as `Cmd+Shift+O` on macOS.

#### Scenario: Default shortcut
- **GIVEN** the user has not changed Mindful's configuration
- **WHEN** the Browser has focus with exactly one note selected and the user presses `Ctrl+Shift+O` (`Cmd+Shift+O` on macOS)
- **THEN** Mindful's editor opens showing that note

#### Scenario: Custom shortcut
- **GIVEN** the user set a different valid shortcut in Mindful's configuration
- **WHEN** the user opens a new Browser window and presses that shortcut with exactly one note selected
- **THEN** Mindful's editor opens showing that note

#### Scenario: Shortcut disabled
- **GIVEN** the user set the shortcut configuration to an empty value
- **WHEN** the user opens a new Browser window
- **THEN** the action remains available from the menus without a keyboard shortcut

### Requirement: Editor shows all note fields

The editor SHALL show every field of the note in the note type's field order, each labeled with its field name.

#### Scenario: Open a note with several fields
- **GIVEN** a note whose note type defines Front, Back, and Extra fields
- **WHEN** the note opens in the editor
- **THEN** the editor shows three editable fields labeled Front, Back, and Extra in that order

### Requirement: Fields convert to Markdown only when lossless

When a note opens, the editor SHALL show a field as Markdown only if converting that Markdown back to HTML gives content equivalent to the stored field. Equivalent means differences are limited to whitespace and interchangeable markup.

#### Scenario: Simple formatted field
- **GIVEN** a field containing bold, italic, line breaks, lists, and links
- **WHEN** the note opens in the editor
- **THEN** the field is shown in Markdown mode with that formatting expressed as Markdown

#### Scenario: Empty field
- **GIVEN** an empty field
- **WHEN** the note opens in the editor
- **THEN** the field is shown in Markdown mode as empty text

### Requirement: Unconvertible fields fall back to HTML

A field that cannot convert to Markdown without loss SHALL be shown and edited as raw HTML, with a visible indication that it is in HTML mode.

#### Scenario: Field with unsupported markup
- **GIVEN** a field containing markup Markdown cannot represent, such as a table or inline color styling
- **WHEN** the note opens in the editor
- **THEN** the field is shown as its exact stored HTML and marked as HTML mode

#### Scenario: Save an HTML-mode field
- **GIVEN** a field shown in HTML mode
- **WHEN** the user edits it and saves
- **THEN** the field is stored exactly as the user typed it

### Requirement: Anki-specific content is preserved

Converting fields between HTML and Markdown SHALL preserve cloze deletions, sound tags, MathJax expressions, and image references as editable text.

#### Scenario: Cloze deletion
- **GIVEN** a field containing `{{c1::answer::hint}}`
- **WHEN** the note opens and is saved after editing a different part of the field
- **THEN** the stored field still contains `{{c1::answer::hint}}`

#### Scenario: MathJax and sound
- **GIVEN** a field containing `\(x_1^2\)` and `[sound:clip_one.mp3]`
- **WHEN** the note opens in Markdown mode and is saved after editing other text
- **THEN** both expressions are stored unchanged and are not altered by Markdown escaping or emphasis rules

#### Scenario: Image reference
- **GIVEN** a field containing an image with a media file name
- **WHEN** the note opens in Markdown mode and is saved after editing other text
- **THEN** the stored field still references the same media file

### Requirement: Save writes only changed fields

Saving SHALL write only fields whose content the user changed. Unchanged fields MUST keep their exact stored HTML.

#### Scenario: Edit one field
- **GIVEN** a note opened in the editor
- **WHEN** the user changes only the Back field and saves
- **THEN** the Back field is updated and every other field is unchanged

#### Scenario: Save without changes
- **GIVEN** a note opened in the editor with no edits
- **WHEN** the user looks at the save control
- **THEN** saving is unavailable and the collection is not modified

### Requirement: Save is a single undoable operation

Saving a note SHALL be a single undoable collection operation that refreshes Anki's views.

#### Scenario: Undo a save
- **GIVEN** the user saved changes to a note in the editor
- **WHEN** the user chooses Undo in Anki
- **THEN** every field saved by that operation returns to its previous content

#### Scenario: Browser reflects the save
- **GIVEN** the Browser shows the note being edited
- **WHEN** the user saves changes in the editor
- **THEN** the Browser shows the updated field content without being reopened

### Requirement: Concurrent changes are not overwritten

Saving SHALL fail without writing if the note was changed or deleted after it opened in the editor. The user's unsaved edits MUST be kept.

#### Scenario: Note edited elsewhere
- **GIVEN** a note is open in the editor
- **AND** the same note is then changed in Anki's own editor
- **WHEN** the user saves in Mindful's editor
- **THEN** nothing is written, the user is told the note changed elsewhere, and the unsaved edits remain in the editor

#### Scenario: Note deleted
- **GIVEN** a note is open in the editor
- **AND** the note is then deleted
- **WHEN** the user saves in Mindful's editor
- **THEN** nothing is written and the user is told the note no longer exists

### Requirement: Unsaved edits are not lost silently

The editor SHALL ask for confirmation before discarding unsaved edits, and SHALL NOT modify the collection without an explicit save.

#### Scenario: Close with unsaved edits
- **GIVEN** the user changed a field without saving
- **WHEN** the user closes the editor
- **THEN** the editor asks whether to discard the edits and stays open if the user cancels

#### Scenario: Open another note with unsaved edits
- **GIVEN** the editor has unsaved edits
- **WHEN** the user opens a different note from the Browser
- **THEN** the editor asks whether to discard the edits before showing the other note

#### Scenario: Close without edits
- **GIVEN** the user made no edits
- **WHEN** the user closes the editor
- **THEN** it closes without prompting and the collection is unchanged

### Requirement: Card preview beside the fields

The editor SHALL display a resizable card-preview pane to the right of the note fields. When a note has a previewable card or variant, the pane SHALL initially show its front.

#### Scenario: Open a note with a card
- **GIVEN** a note has an existing card
- **WHEN** the note opens in Mindful's editor
- **THEN** the fields remain editable on the left and the rendered front of a card appears on the right

#### Scenario: Resize the panes
- **WHEN** the user adjusts the divider between the fields and preview
- **THEN** both panes remain usable and the displayed note and draft are unchanged

### Requirement: Select card variants and sides

The preview SHALL let the user select any existing card of the note and switch between its front and back. The selected card and side SHALL remain selected through edits while that card remains available.

#### Scenario: Preview multiple existing cards
- **GIVEN** a note has several cards
- **WHEN** the user chooses another card in the preview
- **THEN** the preview shows that card rather than only the card selected in the Browser

#### Scenario: Show the back
- **GIVEN** the preview shows a card's front
- **WHEN** the user selects its back
- **THEN** the preview shows the answer rendered for the same card and current draft

#### Scenario: Continue viewing the selected side while editing
- **GIVEN** the user is viewing the back of a card
- **WHEN** the user edits a field and that card remains available
- **THEN** the preview refreshes the same card's back

### Requirement: Preview draft-only card variants

For standard note types, the preview SHALL offer each card template. For cloze note types, it SHALL offer existing cards and cloze numbers present in the draft. A variant without an existing card MUST be identified as preview-only, not as a saved or guaranteed-to-be-generated card.

#### Scenario: Preview a template without an existing card
- **GIVEN** a standard note type has a template for which the note has no existing card
- **WHEN** the user selects that template in the preview
- **THEN** its front and back are available as a preview-only variant

#### Scenario: Add an unsaved cloze
- **GIVEN** a cloze note has an existing first card
- **WHEN** the user adds a second cloze deletion without saving
- **THEN** the second cloze becomes selectable as a preview-only variant without creating a card

#### Scenario: A draft-only cloze is removed
- **GIVEN** a selected cloze variant has no existing card
- **WHEN** its last deletion is removed from the draft
- **THEN** the variant is removed and the preview selects an available variant or shows an empty state

#### Scenario: Save creates a previously preview-only card
- **GIVEN** a draft-only variant has been selected
- **WHEN** a successful save creates the corresponding card
- **THEN** the card remains selectable and is no longer labeled preview-only

### Requirement: Preview reflects the current draft

The preview SHALL update automatically from the current draft without requiring a save. Changed fields SHALL use the HTML a save would produce; unchanged fields SHALL use their exact stored HTML. A stale render MUST NOT replace a newer draft, card, side, or note.

#### Scenario: Edit Markdown
- **GIVEN** the selected card includes a Markdown-mode field
- **WHEN** the user changes that field to include bold Markdown
- **THEN** the selected card updates to show the formatted text before the note is saved

#### Scenario: Edit raw HTML
- **GIVEN** the selected card includes an HTML-mode field
- **WHEN** the user changes the field's HTML
- **THEN** the selected card updates using the HTML as typed

#### Scenario: Preserve an unchanged field's exact markup
- **GIVEN** an unchanged field contains `<strong>text</strong>` and the card styling distinguishes `strong` from `b`
- **WHEN** the preview renders the card
- **THEN** it uses the stored `strong` markup instead of a normalized Markdown round trip

#### Scenario: Edits arrive faster than rendering
- **WHEN** the user makes successive edits or changes the selected card, side, or note before an earlier preview finishes
- **THEN** the pane eventually shows only the latest requested state

#### Scenario: Switch notes
- **GIVEN** the user confirms discarding edits and opens another note
- **WHEN** the new note is displayed
- **THEN** its preview replaces the previous note's preview

### Requirement: Render Anki card content

The preview SHALL use Anki card-template preview semantics, including the selected template, note-type styling, cloze substitutions, local media, and MathJax. The pane SHALL disclose when transient rendering cannot represent card-specific context and the result may differ from review.

#### Scenario: Template styling and answer
- **GIVEN** a card template uses note-type CSS and includes the front on its back
- **WHEN** the user views either side
- **THEN** the preview applies the template and styling to the current draft

#### Scenario: Cloze rendering
- **GIVEN** a cloze variant contains an answer and hint
- **WHEN** the user views its front and then its back
- **THEN** the front hides the answer as Anki's preview does and the back reveals it

#### Scenario: Media and mathematics
- **GIVEN** a card contains a collection image, a sound reference, and a MathJax expression
- **WHEN** its preview is shown
- **THEN** the image and mathematics render and the user can play the sound

#### Scenario: Refresh a card with sound
- **GIVEN** the selected card contains a sound reference
- **WHEN** an edit refreshes the preview
- **THEN** the refresh does not automatically start or restart the sound

#### Scenario: Card-specific context is unavailable
- **GIVEN** a transient preview cannot supply the actual card's deck, flag, or other card-specific context
- **WHEN** that card is previewed
- **THEN** the pane indicates that the result may differ from the card in review

### Requirement: Previewing does not persist edits

Previewing MUST NOT modify the collection, create or update cards, change scheduling, or add an undoable operation. The existing explicit Save operation remains the only way to persist note edits.

#### Scenario: Preview an unsaved edit
- **GIVEN** the user has edited a field without saving
- **WHEN** the preview refreshes or the user changes card or side
- **THEN** the note, cards, scheduling, and undo history remain unchanged and the draft remains unsaved

#### Scenario: Rendering would generate collection media
- **GIVEN** previewing content would require generating a new collection media file
- **WHEN** the preview is rendered without saving
- **THEN** it does not generate that file and indicates any content it cannot display

### Requirement: Preview failures preserve editing

If a preview cannot be rendered, the editor SHALL show an understandable preview status without discarding the draft or preventing the existing save and discard workflows. It SHALL recover on a later successful render.

#### Scenario: Rendering fails
- **GIVEN** the editor contains unsaved changes
- **WHEN** card rendering fails
- **THEN** the pane shows an error instead of a misleading stale card and the edits remain available

#### Scenario: No previewable variant
- **WHEN** the note has no existing card or previewable variant
- **THEN** the pane shows an empty state and the fields remain editable

#### Scenario: A later render succeeds
- **GIVEN** the preview previously showed an error or empty state
- **WHEN** an edit or selection makes a card renderable
- **THEN** the preview replaces the status with the current card
