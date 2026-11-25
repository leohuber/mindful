from mindful.core.note_draft import NoteDraft, NoteSnapshot


def _draft() -> NoteDraft:
    snapshot = NoteSnapshot(1, 100, (("Front", "<b>front</b>"), ("Back", "back"), ("Extra", '<span style="x">extra</span>')))
    return NoteDraft.from_snapshot(snapshot)


def test_fields_keep_note_type_order_and_modes() -> None:
    draft = _draft()
    assert [(field.name, field.mode) for field in draft.fields] == [("Front", "markdown"), ("Back", "markdown"), ("Extra", "html")]
    assert draft.fields[0].text == "**front**"


def test_no_edits_produce_no_changes() -> None:
    draft = _draft()
    assert not draft.has_changes
    assert draft.changed_html() == {}


def test_edit_to_one_field_changes_only_that_index() -> None:
    draft = _draft()
    draft.set_text(1, "new *back*")
    assert draft.has_changes
    assert draft.changed_html() == {1: "new <i>back</i>"}


def test_edited_html_mode_field_is_saved_verbatim() -> None:
    draft = _draft()
    draft.set_text(2, '<span style="y">  raw **text** </span>')
    assert draft.changed_html() == {2: '<span style="y">  raw **text** </span>'}


def test_editing_then_reverting_field_counts_as_unchanged() -> None:
    draft = _draft()
    draft.set_text(0, "changed")
    draft.set_text(0, "**front**")
    assert not draft.has_changes
    assert draft.changed_html() == {}
