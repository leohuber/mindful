"""Snapshot and draft model for editing one note's fields."""

from dataclasses import dataclass, field

from .html_format import compact_html, format_html


@dataclass(frozen=True)
class NoteSnapshot:
    """Stored state of a note when it was loaded."""

    note_id: int
    mod: int
    fields: tuple[tuple[str, str], ...]

    @property
    def field_html(self) -> tuple[str, ...]:
        """Stored HTML of each field in note type order."""
        return tuple(html for _, html in self.fields)


@dataclass
class FieldDraft:
    """Editor state of one field."""

    name: str
    formatted: bool
    original_text: str
    text: str

    @property
    def changed(self) -> bool:
        """Whether the editor text differs from the text it opened with."""
        return self.text != self.original_text

    def to_html(self) -> str:
        """Convert the editor text to stored HTML.

        Returns:
            Compact HTML for fields opened with display formatting, or the verbatim text otherwise.
        """
        return compact_html(self.text) if self.formatted else self.text


@dataclass
class NoteDraft:
    """Editable fields of a note, tied to the snapshot they were opened from."""

    snapshot: NoteSnapshot
    fields: list[FieldDraft] = field(default_factory=list)

    @classmethod
    def from_snapshot(cls, snapshot: NoteSnapshot) -> "NoteDraft":
        """Open every field as HTML, formatted for reading when that is reversible.

        Returns:
            A draft with no changes.
        """
        drafts = []
        for name, html in snapshot.fields:
            formatted = format_html(html)
            text = html if formatted is None else formatted
            drafts.append(FieldDraft(name, formatted is not None, text, text))
        return cls(snapshot, drafts)

    def set_text(self, index: int, text: str) -> None:
        """Replace the editor text of one field."""
        self.fields[index].text = text

    @property
    def has_changes(self) -> bool:
        """Whether any field differs from the text it opened with."""
        return any(draft.changed for draft in self.fields)

    def changed_html(self) -> dict[int, str]:
        """Build the HTML to store for changed fields only.

        Returns:
            A mapping of field index to new stored HTML.
        """
        return {index: draft.to_html() for index, draft in enumerate(self.fields) if draft.changed}

    def preview_html(self) -> tuple[str, ...]:
        """Build the field HTML represented by the current draft.

        Returns:
            Save-ready HTML for changed fields and the original HTML for unchanged fields.
        """
        changes = self.changed_html()
        return tuple(changes.get(index, html) for index, html in enumerate(self.snapshot.field_html))
