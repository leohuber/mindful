# Spec Delta

## ADDED Requirements

### Requirement: Move to the previous or next note

The editor SHALL offer previous-note and next-note controls. They open the nearest different note before or after the Browser's current row, in the Browser's current order, and select that note's row in the Browser.

#### Scenario: Move to the next note
- **GIVEN** the Browser lists notes A, B and C, and B is open in the editor and selected in the Browser
- **WHEN** the user chooses the next-note control
- **THEN** the editor shows note C and the Browser selects C's row

#### Scenario: Move to the previous note
- **GIVEN** the Browser lists notes A, B and C, and B is open in the editor and selected in the Browser
- **WHEN** the user chooses the previous-note control
- **THEN** the editor shows note A and the Browser selects A's row

#### Scenario: Several cards of one note in card mode
- **GIVEN** the Browser is in card mode, and the rows after the current one belong to the same note before a row of another note
- **WHEN** the user chooses the next-note control
- **THEN** the editor shows the other note instead of reopening the same note

### Requirement: Navigation unavailable at the ends of the list

A previous-note or next-note control SHALL be disabled when the Browser has no row in that direction. If every row in that direction belongs to the current note, choosing the control SHALL leave the editor and the Browser selection unchanged and tell the user there is no other note.

#### Scenario: Last row in the list
- **GIVEN** the Browser's current row is its last row
- **WHEN** the editor shows a note
- **THEN** the next-note control is disabled and the previous-note control is enabled if an earlier row exists

#### Scenario: Single row in the list
- **GIVEN** the Browser lists only one row
- **WHEN** the editor shows that note
- **THEN** both controls are disabled

#### Scenario: Only cards of the same note remain
- **GIVEN** the Browser is in card mode and every row after the current one belongs to the current note
- **WHEN** the user chooses the next-note control
- **THEN** the editor and the Browser selection are unchanged and the user is told there is no next note

### Requirement: Navigation keeps unsaved edits safe

Moving to another note with unsaved edits SHALL ask whether to discard them. If the user cancels, the editor and the Browser selection SHALL stay unchanged. Moving MUST NOT save the note.

#### Scenario: Cancel moving with unsaved edits
- **GIVEN** the editor has unsaved edits
- **WHEN** the user chooses the next-note control and cancels the confirmation
- **THEN** the editor keeps the same note and edits, and the Browser selection is unchanged

#### Scenario: Discard and move
- **GIVEN** the editor has unsaved edits
- **WHEN** the user chooses the next-note control and confirms discarding
- **THEN** the editor shows the next note, the edits are discarded and the collection is unchanged

#### Scenario: Move without edits
- **GIVEN** the editor has no unsaved edits
- **WHEN** the user chooses the next-note control
- **THEN** the editor shows the next note without asking

### Requirement: Navigation keyboard shortcuts

The previous-note and next-note actions SHALL use shortcuts from the configuration keys `previous_note_shortcut` and `next_note_shortcut`, defaulting to `Ctrl+Alt+Left` and `Ctrl+Alt+Right` (`Cmd+Option+Left/Right` on macOS). They SHALL work while a field has focus; unmodified arrow keys SHALL keep moving the text cursor.

#### Scenario: Default shortcut while editing a field
- **GIVEN** the user has not changed Mindful's configuration and a field has focus
- **WHEN** the user presses `Ctrl+Alt+Right` (`Cmd+Option+Right` on macOS)
- **THEN** the editor moves to the next note as the next-note control does

#### Scenario: Plain arrow keys edit text
- **GIVEN** a field has focus
- **WHEN** the user presses Left or Right without modifiers
- **THEN** the text cursor moves within the field and the editor stays on the same note

#### Scenario: Custom shortcut
- **GIVEN** the user set `next_note_shortcut` to a different valid shortcut
- **WHEN** the user opens a new editor window and presses that shortcut
- **THEN** the editor moves to the next note

#### Scenario: Invalid shortcut
- **GIVEN** the user set `previous_note_shortcut` to an invalid value
- **WHEN** the user opens a new editor window
- **THEN** the previous-note action uses `Ctrl+Alt+Left`

#### Scenario: Shortcut disabled
- **GIVEN** the user set `next_note_shortcut` to an empty value
- **WHEN** the user opens a new editor window
- **THEN** the next-note control remains available without a keyboard shortcut
