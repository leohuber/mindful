from collections.abc import Callable, Mapping

import pytest

from mindful.application.note_editing import NoChangesError, NoteChangedError, NoteDeletedError, NoteEditing
from mindful.core.note_draft import NoteDraft, NoteSnapshot


class InMemoryNoteStore:
    def __init__(self) -> None:
        self.notes = {1: NoteSnapshot(1, 100, (("Front", "front"), ("Back", "back")))}
        self.saves: list[tuple[NoteSnapshot, dict[int, str]]] = []

    def load(self, note_id: int) -> NoteSnapshot:
        if note_id not in self.notes:
            raise NoteDeletedError
        return self.notes[note_id]

    def save(
        self,
        expected: NoteSnapshot,
        changes: Mapping[int, str],
        on_success: Callable[[NoteSnapshot], None],
        on_failure: Callable[[Exception], None],
    ) -> None:
        self.saves.append((expected, dict(changes)))
        current = self.notes.get(expected.note_id)
        if current is None:
            on_failure(NoteDeletedError())
            return
        if current != expected:
            on_failure(NoteChangedError())
            return
        fields = [(name, changes.get(index, html)) for index, (name, html) in enumerate(current.fields)]
        saved = NoteSnapshot(current.note_id, current.mod + 1, tuple(fields))
        self.notes[saved.note_id] = saved
        on_success(saved)


def _save(editing: NoteEditing, draft: NoteDraft) -> tuple[list[NoteDraft], list[Exception]]:
    saved: list[NoteDraft] = []
    failed: list[Exception] = []
    editing.save(draft, saved.append, failed.append)
    return saved, failed


def test_opening_builds_draft() -> None:
    draft = NoteEditing(InMemoryNoteStore()).open(1)
    assert [field.name for field in draft.fields] == ["Front", "Back"]
    assert not draft.has_changes


def test_opening_missing_note_raises_deleted() -> None:
    with pytest.raises(NoteDeletedError):
        NoteEditing(InMemoryNoteStore()).open(2)


def test_saving_sends_only_changed_fields_with_expected_snapshot() -> None:
    store = InMemoryNoteStore()
    editing = NoteEditing(store)
    draft = editing.open(1)
    draft.set_text(1, "<b>new</b>")
    saved, failed = _save(editing, draft)
    assert store.saves == [(draft.snapshot, {1: "<b>new</b>"})]
    assert failed == []
    assert saved[0].snapshot.fields == (("Front", "front"), ("Back", "<b>new</b>"))
    assert not saved[0].has_changes


def test_conflicts_and_deletions_are_distinct_errors() -> None:
    store = InMemoryNoteStore()
    editing = NoteEditing(store)
    changed = editing.open(1)
    changed.set_text(0, "mine")
    store.notes[1] = NoteSnapshot(1, 101, (("Front", "theirs"), ("Back", "back")))
    _, failed = _save(editing, changed)
    assert isinstance(failed[0], NoteChangedError)

    deleted = editing.open(1)
    deleted.set_text(0, "mine")
    del store.notes[1]
    _, failed = _save(editing, deleted)
    assert isinstance(failed[0], NoteDeletedError)
    assert deleted.fields[0].text == "mine"


def test_saving_without_changes_is_rejected() -> None:
    store = InMemoryNoteStore()
    editing = NoteEditing(store)
    with pytest.raises(NoChangesError):
        _save(editing, editing.open(1))
    assert store.saves == []
