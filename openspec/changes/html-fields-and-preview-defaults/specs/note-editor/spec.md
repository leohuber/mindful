# Spec Delta

## ADDED Requirements

### Requirement: Fields are edited as HTML

The editor SHALL show and edit every field as HTML. It SHALL NOT convert fields to or from another markup language or mark fields with an editing mode.

#### Scenario: Field with simple formatting
- **GIVEN** a field containing bold text and a line break
- **WHEN** the note opens in the editor
- **THEN** the field shows the `<b>` and `<br>` markup as editable HTML

#### Scenario: Empty field
- **GIVEN** an empty field
- **WHEN** the note opens in the editor
- **THEN** the field is shown as empty text

#### Scenario: Save a field shown as stored
- **GIVEN** a field shown exactly as stored because it cannot be formatted safely
- **WHEN** the user edits it and saves
- **THEN** the field is stored exactly as the user typed it

### Requirement: Readable HTML display

When a note opens, the editor SHALL display each field with line breaks and indentation added only where they do not change how the card renders: at block-level element boundaries and after line breaks. A field for which this cannot be guaranteed SHALL be shown exactly as stored.

#### Scenario: Single-line block markup
- **GIVEN** a field stored as `<div>One</div><ul><li>A</li><li>B</li></ul>` on one line
- **WHEN** the note opens in the editor
- **THEN** each block element starts on its own line with list items indented

#### Scenario: Inline markup stays on one line
- **GIVEN** a field containing `<b>a</b><i>b</i>` within a paragraph
- **WHEN** the note opens in the editor
- **THEN** no line break or indentation is inserted between the inline elements

#### Scenario: Whitespace-sensitive content
- **GIVEN** a field containing a `<pre>` block
- **WHEN** the note opens in the editor
- **THEN** the content of the `<pre>` block is shown unchanged

#### Scenario: Open and close without edits
- **GIVEN** a field was displayed with added line breaks
- **WHEN** the user closes the editor without editing
- **THEN** the editor closes without prompting and the stored field is unchanged

### Requirement: Compact HTML on save

Saving a field that was displayed with added formatting SHALL store compact HTML, with the line breaks and indentation at block-level boundaries removed. The rendered card MUST look the same as it would with the formatted text.

#### Scenario: Edit a formatted field
- **GIVEN** a field stored on one line and displayed with added line breaks
- **WHEN** the user changes a word inside one element and saves
- **THEN** the stored field is on one line and differs from the original only by that word

#### Scenario: Preview matches the saved form
- **GIVEN** a formatted field has unsaved edits
- **WHEN** the preview refreshes
- **THEN** it renders the compact HTML that saving would store

### Requirement: HTML syntax highlighting

Field editors SHALL visually distinguish HTML tags, attribute names, attribute values, comments, cloze deletions and MathJax delimiters from the surrounding text, using colors that stay readable in light and dark themes.

#### Scenario: Highlight markup while editing
- **GIVEN** a field containing `<span class="hint">{{c1::cell}}</span>`
- **WHEN** the note opens or the user types further markup
- **THEN** the tag, the attribute name, the attribute value and the cloze deletion are shown in distinct styles

### Requirement: Configurable field font size

Field editors SHALL use a monospace font at a point size read from the add-on configuration key `field_font_size`, defaulting to 14. A missing or invalid value, or one outside 8 to 48, SHALL fall back to the default.

#### Scenario: Default font size
- **GIVEN** the user has not changed Mindful's configuration
- **WHEN** a note opens in the editor
- **THEN** every field is shown in a monospace font at 14 points

#### Scenario: Custom font size
- **GIVEN** the user set `field_font_size` to 18
- **WHEN** a note is opened in a newly opened editor
- **THEN** every field is shown at 18 points

#### Scenario: Invalid font size
- **GIVEN** the user set `field_font_size` to a value outside 8 to 48 or to a non-number
- **WHEN** a note opens in the editor
- **THEN** every field is shown at 14 points

## MODIFIED Requirements

### Requirement: Anki-specific content is preserved

Displaying, formatting and compacting fields SHALL preserve cloze deletions, sound tags, MathJax expressions, and image references as editable text.

#### Scenario: Cloze deletion
- **GIVEN** a field containing `{{c1::answer::hint}}`
- **WHEN** the note opens and is saved after editing a different part of the field
- **THEN** the stored field still contains `{{c1::answer::hint}}`

#### Scenario: MathJax and sound
- **GIVEN** a field containing `\(x_1^2\)` and `[sound:clip_one.mp3]`
- **WHEN** the note opens and is saved after editing other text
- **THEN** both expressions are stored unchanged and no line break is inserted inside them

#### Scenario: Image reference
- **GIVEN** a field containing an image with a media file name
- **WHEN** the note opens and is saved after editing other text
- **THEN** the stored field still references the same media file

### Requirement: Card preview beside the fields

The editor SHALL display a resizable card-preview pane to the right of the note fields. When the editor opens, the fields and the preview SHALL share the available width equally. When a note has a previewable card or variant, the pane SHALL initially show its back.

#### Scenario: Open a note with a card
- **GIVEN** a note has an existing card
- **WHEN** the note opens in Mindful's editor
- **THEN** the fields remain editable on the left and the rendered back of a card appears on the right

#### Scenario: Equal initial split
- **WHEN** the editor window opens
- **THEN** the fields pane and the preview pane have equal widths

#### Scenario: Resize the panes
- **WHEN** the user adjusts the divider between the fields and preview
- **THEN** both panes remain usable and the displayed note and draft are unchanged

### Requirement: Select card variants and sides

The preview SHALL let the user select any existing card of the note and switch between its front and back. Selecting a different card SHALL show its back. The selected card and side SHALL remain selected through edits while that card remains available.

#### Scenario: Preview multiple existing cards
- **GIVEN** a note has several cards
- **WHEN** the user chooses another card in the preview
- **THEN** the preview shows the back of that card rather than only the card selected in the Browser

#### Scenario: Show the front
- **GIVEN** the preview shows a card's back
- **WHEN** the user selects its front
- **THEN** the preview shows the question rendered for the same card and current draft

#### Scenario: Show the back
- **GIVEN** the user switched the preview to a card's front
- **WHEN** the user selects its back
- **THEN** the preview shows the answer rendered for the same card and current draft

#### Scenario: Continue viewing the selected side while editing
- **GIVEN** the user is viewing the front of a card
- **WHEN** the user edits a field and that card remains available
- **THEN** the preview refreshes the same card's front

## REMOVED Requirements

### Requirement: Fields convert to Markdown only when lossless

**Reason**: Fields are no longer converted to Markdown. Every field is edited as HTML.
**Migration**: None. Previously saved fields are ordinary HTML and open as HTML.

### Requirement: Unconvertible fields fall back to HTML

**Reason**: With every field edited as HTML, there is no fallback mode or HTML-mode indication.
**Migration**: Covered by "Fields are edited as HTML" and "Readable HTML display".
