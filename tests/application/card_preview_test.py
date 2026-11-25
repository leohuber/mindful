from collections.abc import Callable

import pytest

from mindful.application.card_preview import (
    CardPreviewError,
    CardVariant,
    PreviewController,
    PreviewSelection,
    RenderedCard,
    cloze_variants,
    standard_variants,
)
from mindful.core.note_draft import NoteDraft, NoteSnapshot


class PreviewCatalog:
    def __init__(self, *variants: CardVariant) -> None:
        self.available = variants

    def variants(self) -> tuple[CardVariant, ...]:
        return self.available


class PreviewSession:
    def __init__(self) -> None:
        self.requests: list[tuple[tuple[str, ...], int]] = []
        self.available = (CardVariant(0, "Card 1", True),)
        self.on_variants: Callable[[], None] | None = None
        self.on_render: Callable[[], None] | None = None

    def variants(self, _fields: tuple[str, ...]) -> tuple[CardVariant, ...]:
        if self.on_variants is not None:
            self.on_variants()
        return self.available

    def render(self, fields: tuple[str, ...], ordinal: int) -> RenderedCard:
        self.requests.append((fields, ordinal))
        if self.on_render is not None:
            self.on_render()
        return RenderedCard(fields[0], fields[-1])

    def play_audio(self, _command: str) -> None:
        pass


class PreviewSource:
    def __init__(self, snapshot: NoteSnapshot) -> None:
        self.snapshot = snapshot
        self.session = PreviewSession()
        self.unavailable = False

    def open(self, expected: NoteSnapshot) -> PreviewSession:
        if self.unavailable or expected != self.snapshot:
            raise CardPreviewError
        return self.session


def test_standard_variants_include_templates_and_existing_cards_in_order() -> None:
    variants = standard_variants(("Front", "Reverse", "Extra"), (2, 0, 4))

    assert variants == (
        CardVariant(0, "Front", True),
        CardVariant(1, "Reverse", False),
        CardVariant(2, "Extra", True),
        CardVariant(4, "Card 5", True),
    )


def test_cloze_variants_include_existing_cards_and_draft_numbers_in_order() -> None:
    variants = cloze_variants((3, 1, 3, 0), (4, 0))

    assert variants == (CardVariant(0, "Cloze 1", True), CardVariant(2, "Cloze 3", False), CardVariant(4, "Cloze 5", True))


def test_initial_selection_prefers_an_existing_card() -> None:
    catalog = PreviewCatalog(CardVariant(0, "First", False), CardVariant(1, "Second", True))
    selection = PreviewSelection()
    selection.update_variants(catalog.variants())

    assert selection.ordinal == 1
    assert selection.side == "front"


def test_selection_and_side_survive_variant_refresh_and_save() -> None:
    catalog = PreviewCatalog(CardVariant(0, "Cloze 1", True), CardVariant(1, "Cloze 2", False))
    selection = PreviewSelection()
    selection.update_variants(catalog.variants())
    selection.select_variant(1)
    selection.select_side("back")

    catalog.available = (CardVariant(0, "Cloze 1", True), CardVariant(1, "Cloze 2", True))
    selection.update_variants(catalog.variants())

    assert selection.ordinal == 1
    assert selection.side == "back"
    assert selection.variants[1].exists


def test_removed_selection_falls_back_to_first_existing_card() -> None:
    selection = PreviewSelection()
    selection.update_variants((CardVariant(0, "First", False), CardVariant(1, "Second", True), CardVariant(2, "Third", False)))
    selection.select_variant(2)
    selection.select_side("back")

    selection.update_variants((CardVariant(0, "First", False), CardVariant(1, "Second", True)))

    assert selection.ordinal == 1
    assert selection.side == "front"


def test_empty_selection_recovers_when_preview_only_variant_appears() -> None:
    selection = PreviewSelection()
    selection.update_variants(())
    assert selection.ordinal is None

    selection.update_variants((CardVariant(3, "Cloze 4", False),))
    assert selection.ordinal == 3
    assert selection.side == "front"


def test_unavailable_variant_cannot_be_selected() -> None:
    selection = PreviewSelection()
    with pytest.raises(ValueError, match=r"^1$"):
        selection.select_variant(1)


def test_preview_renders_the_draft_without_changing_the_opened_snapshot() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "<strong>front</strong>"), ("Back", "old")))
    source = PreviewSource(snapshot)
    controller = PreviewController(source)
    draft = NoteDraft.from_snapshot(snapshot)
    draft.set_text(1, "new *back*")

    rendered = controller.render(draft)

    assert rendered == RenderedCard("<strong>front</strong>", "new <i>back</i>")
    assert source.session.requests == [(("<strong>front</strong>", "new <i>back</i>"), 0)]
    assert source.snapshot == snapshot
    assert draft.has_changes


def test_preview_recovers_when_a_session_becomes_available() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "front"),))
    source = PreviewSource(snapshot)
    controller = PreviewController(source)
    draft = NoteDraft.from_snapshot(snapshot)
    source.unavailable = True

    with pytest.raises(CardPreviewError):
        controller.render(draft)
    source.unavailable = False

    assert controller.render(draft) == RenderedCard("front", "front")


def test_preview_failure_keeps_an_inconsistent_draft_unchanged() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "front"),))
    source = PreviewSource(NoteSnapshot(1, 101, (("Front", "changed elsewhere"),)))
    controller = PreviewController(source)
    draft = NoteDraft.from_snapshot(snapshot)
    draft.set_text(0, "my edit")

    with pytest.raises(CardPreviewError):
        controller.render(draft)

    assert draft.fields[0].text == "my edit"
    assert draft.has_changes
    assert source.snapshot.fields == (("Front", "changed elsewhere"),)


def test_replacing_or_closing_a_note_invalidates_pending_results() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "front"),))
    source = PreviewSource(snapshot)
    controller = PreviewController(source)
    controller.open(snapshot)
    previous_generation = controller.generation

    controller.invalidate()
    assert not controller.is_current(previous_generation)
    current_generation = controller.generation
    controller.close()
    assert not controller.is_current(current_generation)


def test_rapid_edits_discard_an_older_render_and_show_the_latest_draft() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "original"),))
    source = PreviewSource(snapshot)
    controller = PreviewController(source)
    draft = NoteDraft.from_snapshot(snapshot)
    controller.open(snapshot)
    draft.set_text(0, "first edit")
    controller.invalidate()

    def edit_again() -> None:
        draft.set_text(0, "latest **edit**")
        controller.invalidate()

    source.session.on_render = edit_again
    assert controller.render(draft) is None

    source.session.on_render = None
    assert controller.render(draft) == RenderedCard("latest <b>edit</b>", "latest <b>edit</b>")


def test_changing_card_and_side_during_render_discards_the_old_result() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "front"),))
    source = PreviewSource(snapshot)
    source.session.available = (CardVariant(0, "First", True), CardVariant(1, "Second", True))
    controller = PreviewController(source)
    draft = NoteDraft.from_snapshot(snapshot)
    controller.open(snapshot)
    controller.render(draft)

    def select_another_card() -> None:
        controller.selection.select_variant(1)
        controller.selection.select_side("back")
        controller.invalidate()

    source.session.on_render = select_another_card
    assert controller.render(draft) is None
    assert controller.selection.ordinal == 1
    assert controller.selection.side == "back"

    source.session.on_render = None
    assert controller.render(draft) == RenderedCard("front", "front")
    assert source.session.requests[-1][1] == 1


def test_switching_notes_during_variant_discovery_does_not_replace_the_new_selection() -> None:
    first = NoteSnapshot(1, 100, (("Front", "first note"),))
    second = NoteSnapshot(2, 101, (("Front", "second note"),))
    source = PreviewSource(first)
    controller = PreviewController(source)
    controller.open(first)

    def switch_notes() -> None:
        source.snapshot = second
        controller.open(second)

    source.session.on_variants = switch_notes
    assert controller.render(NoteDraft.from_snapshot(first)) is None
    assert controller.selection.variants == ()

    source.session.on_variants = None
    assert controller.render(NoteDraft.from_snapshot(second)) == RenderedCard("second note", "second note")


def test_successful_save_reopens_metadata_and_keeps_the_selected_variant_and_side() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "original"),))
    saved = NoteSnapshot(1, 101, (("Front", "saved"),))
    source = PreviewSource(snapshot)
    source.session.available = (CardVariant(0, "Card 1", True), CardVariant(1, "Card 2", False))
    controller = PreviewController(source)
    controller.open(snapshot)
    controller.render(NoteDraft.from_snapshot(snapshot))
    controller.selection.select_variant(1)
    controller.selection.select_side("back")
    before_save = controller.generation

    source.snapshot = saved
    source.session.available = (CardVariant(0, "Card 1", True), CardVariant(1, "Card 2", True))
    controller.open(saved, preserve_selection=True)
    rendered = controller.render(NoteDraft.from_snapshot(saved))

    assert not controller.is_current(before_save)
    assert rendered == RenderedCard("saved", "saved")
    assert controller.selection.ordinal == 1
    assert controller.selection.side == "back"
    assert controller.selection.variants[1].exists


def test_closing_during_render_discards_the_late_result() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "front"),))
    source = PreviewSource(snapshot)
    controller = PreviewController(source)
    controller.open(snapshot)
    source.session.on_render = controller.close

    assert controller.render(NoteDraft.from_snapshot(snapshot)) is None
    assert controller.selection.variants == ()


def test_retrying_an_unavailable_session_keeps_the_current_generation() -> None:
    snapshot = NoteSnapshot(1, 100, (("Front", "front"),))
    source = PreviewSource(snapshot)
    controller = PreviewController(source)
    source.unavailable = True
    with pytest.raises(CardPreviewError):
        controller.open(snapshot)
    generation = controller.generation

    source.unavailable = False
    assert controller.render(NoteDraft.from_snapshot(snapshot)) == RenderedCard("front", "front")
    assert controller.is_current(generation)
