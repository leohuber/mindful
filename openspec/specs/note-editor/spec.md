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
