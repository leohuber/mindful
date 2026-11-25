"""Collection-backed note store with undoable, conflict-checked saves."""

from collections.abc import Callable, Mapping

from anki.collection import Collection, OpChanges
from anki.errors import NotFoundError
from anki.notes import Note, NoteId
from aqt.main import AnkiQt
from aqt.operations import CollectionOp

from ..application.note_editing import NoteChangedError, NoteDeletedError
from ..core.note_draft import NoteSnapshot


def snapshot_note(note: Note) -> NoteSnapshot:
    """Capture a note's current fields and modification time.

    Returns:
        The stored note snapshot.
    """
    return NoteSnapshot(int(note.id), int(note.mod), tuple(zip(note.keys(), note.fields, strict=True)))


def get_note(col: Collection, note_id: int) -> Note:
    """Load a note from the collection.

    Returns:
        The loaded note.

    Raises:
        NoteDeletedError: If the note no longer exists.
    """
    try:
        return col.get_note(NoteId(note_id))
    except NotFoundError as error:
        raise NoteDeletedError from error


class CollectionNoteStore:
    """Load and save notes in the open collection of the main window."""

    def __init__(self, mw: AnkiQt) -> None:
        """Use the collection of `mw` when called."""
        self._mw = mw

    def _col(self) -> Collection:
        col = self._mw.col
        if col is None:
            raise NoteDeletedError
        return col

    def load(self, note_id: int) -> NoteSnapshot:
        """Load the stored state of a note.

        Returns:
            The note's snapshot.
        """
        return snapshot_note(get_note(self._col(), note_id))

    def save(
        self,
        expected: NoteSnapshot,
        changes: Mapping[int, str],
        on_success: Callable[[NoteSnapshot], None],
        on_failure: Callable[[Exception], None],
    ) -> None:
        """Write changed fields in one undoable operation if the note is unchanged since `expected`."""
        saved: list[NoteSnapshot] = []

        def op(col: Collection) -> OpChanges:
            note = get_note(col, expected.note_id)
            if snapshot_note(note) != expected:
                raise NoteChangedError
            for index, html in changes.items():
                note.fields[index] = html
            result = col.update_note(note)
            saved.append(snapshot_note(get_note(col, expected.note_id)))
            return result

        CollectionOp(self._mw, op).success(lambda _changes: on_success(saved[0])).failure(on_failure).run_in_background()
