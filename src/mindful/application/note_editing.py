"""Use cases for opening and saving a note in Mindful's editor."""

from collections.abc import Callable, Mapping
from typing import Protocol

from ..core.note_draft import NoteDraft, NoteSnapshot


class NoteEditingError(Exception):
    """Base class for note editing failures the user should be told about."""


class NoteChangedError(NoteEditingError):
    """The note changed after it was opened, so saving would overwrite it."""


class NoteDeletedError(NoteEditingError):
    """The note no longer exists."""


class NoChangesError(NoteEditingError):
    """The draft has no changes to save."""


class NoteStore(Protocol):
    """Loads note snapshots and saves changed fields."""

    def load(self, note_id: int) -> NoteSnapshot:
        """Load the stored state of a note, raising `NoteDeletedError` if it is missing."""
        ...

    def save(
        self,
        expected: NoteSnapshot,
        changes: Mapping[int, str],
        on_success: Callable[[NoteSnapshot], None],
        on_failure: Callable[[Exception], None],
    ) -> None:
        """Write changed fields if the note still matches `expected`, then report the saved snapshot."""
        ...


class NoteEditing:
    """Open notes as drafts and save their changed fields."""

    def __init__(self, store: NoteStore) -> None:
        """Use `store` for all note access."""
        self._store = store

    def open(self, note_id: int) -> NoteDraft:
        """Load a note and build an unchanged draft.

        Returns:
            A draft of the note's fields.
        """
        return NoteDraft.from_snapshot(self._store.load(note_id))

    def save(
        self,
        draft: NoteDraft,
        on_saved: Callable[[NoteDraft], None],
        on_failed: Callable[[Exception], None],
    ) -> None:
        """Save the draft's changed fields and report a fresh draft of the saved note.

        Raises:
            NoChangesError: If the draft has no changes.
        """
        changes = draft.changed_html()
        if not changes:
            raise NoChangesError
        self._store.save(
            draft.snapshot,
            changes,
            lambda snapshot: on_saved(NoteDraft.from_snapshot(snapshot)),
            on_failed,
        )
