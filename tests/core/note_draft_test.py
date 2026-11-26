from mindful.core.note_draft import NoteDraft, NoteSnapshot


def _draft() -> NoteDraft:
    snapshot = NoteSnapshot(1, 100, (("Front", "<div>front</div><div>more</div>"), ("Back", "back"), ("Extra", "<div>a</div>\n<div>b</div>")))
    return NoteDraft.from_snapshot(snapshot)


def test_fields_keep_note_type_order_and_open_formatted_when_reversible() -> None:
    draft = _draft()
    assert [(field.name, field.formatted) for field in draft.fields] == [("Front", True), ("Back", True), ("Extra", False)]
    assert draft.fields[0].text == "<div>front</div>\n<div>more</div>"
    assert draft.fields[2].text == "<div>a</div>\n<div>b</div>"


def test_no_edits_produce_no_changes() -> None:
    draft = _draft()
    assert not draft.has_changes
    assert draft.changed_html() == {}


def test_edited_formatted_field_is_saved_compact() -> None:
    draft = _draft()
    draft.set_text(0, "<div>front</div>\n<div>changed</div>")
    assert draft.has_changes
    assert draft.changed_html() == {0: "<div>front</div><div>changed</div>"}


def test_edited_field_shown_as_stored_is_saved_verbatim() -> None:
    draft = _draft()
    draft.set_text(2, "<div>a</div>\n<div>c</div>")
    assert draft.changed_html() == {2: "<div>a</div>\n<div>c</div>"}


def test_editing_then_reverting_field_counts_as_unchanged() -> None:
    draft = _draft()
    draft.set_text(0, "changed")
    draft.set_text(0, "<div>front</div>\n<div>more</div>")
    assert not draft.has_changes
    assert draft.changed_html() == {}


def test_preview_uses_compact_html_and_preserves_unchanged_markup() -> None:
    draft = _draft()
    draft.set_text(0, "<div>new</div>\n<div>more</div>")

    preview = draft.preview_html()
    draft.set_text(0, "later")

    assert preview == ("<div>new</div><div>more</div>", "back", "<div>a</div>\n<div>b</div>")


def test_preview_restores_exact_markup_when_edit_is_reverted() -> None:
    draft = NoteDraft.from_snapshot(NoteSnapshot(1, 100, (("Front", "<ul><li>front</li></ul>"),)))
    draft.set_text(0, "changed")
    draft.set_text(0, draft.fields[0].original_text)

    assert draft.preview_html() == ("<ul><li>front</li></ul>",)
    assert not draft.has_changes
