"""Read-only Anki card rendering for an unsaved note draft."""

import re
from copy import copy, deepcopy
from typing import override

from anki.cards import Card
from anki.collection import Collection
from anki.consts import MODEL_CLOZE
from anki.decks import DEFAULT_DECK_ID
from anki.models import NotetypeDict
from anki.notes import Note
from anki.template import TemplateRenderContext
from aqt.main import AnkiQt
from aqt.sound import play_clicked_audio

from ..application.card_preview import CardPreviewError, CardVariant, RenderedCard, cloze_variants, standard_variants
from ..application.note_editing import NoteDeletedError
from ..core.note_draft import NoteSnapshot
from .note_store import get_note, snapshot_note

_LEGACY_LATEX = re.compile(r"\[(?:latex|\${1,2})\]", re.IGNORECASE)
_AUDIO_COMMAND = re.compile(r"play:([qa]):([0-9]+)")


class _PreviewCard(Card):
    def __init__(self, col: Collection, note: Note, ordinal: int, original: Card | None) -> None:
        super().__init__(col, id=original.id if original is not None else None)
        self._preview_note = note
        self.ord = ordinal
        if original is None:
            self.did = DEFAULT_DECK_ID
            self.nid = note.id

    @override
    def note(self, reload: bool = False) -> Note:
        """Return the draft note instead of reloading its stored fields."""
        return self._preview_note


class CollectionCardPreview:
    """Open read-only preview sessions in the current collection."""

    def __init__(self, mw: AnkiQt) -> None:
        """Use the collection of `mw` when a note is opened."""
        self._mw = mw

    def open(self, expected: NoteSnapshot) -> "CollectionPreviewSession":
        """Open a transient copy of the note described by `expected`.

        Returns:
            A preview session bound to the opened snapshot.

        Raises:
            CardPreviewError: If the collection or note is unavailable or changed.
        """
        col = self._mw.col
        if col is None:
            message = "The collection is not open."
            raise CardPreviewError(message)
        try:
            note = get_note(col, expected.note_id)
        except NoteDeletedError as error:
            message = "This note no longer exists."
            raise CardPreviewError(message) from error
        if snapshot_note(note) != expected:
            message = "This note changed before its preview opened."
            raise CardPreviewError(message)
        notetype = note.note_type()
        if notetype is None:
            message = "This note's type is unavailable."
            raise CardPreviewError(message)
        return CollectionPreviewSession(col, note, deepcopy(notetype), note.cards())


class CollectionPreviewSession:
    """Render one detached note without writing it to the collection."""

    def __init__(self, col: Collection, note: Note, notetype: NotetypeDict, cards: list[Card]) -> None:
        """Keep the opened note, note type, and card metadata in memory."""
        self._col = col
        self._note = note
        self._notetype = notetype
        self._cards = {card.ord: _PreviewCard(col, note, card.ord, card) for card in cards}
        self._rendered_card: Card | None = None

    def _set_fields(self, fields: tuple[str, ...]) -> None:
        if len(fields) != len(self._note.fields):
            message = "The note's fields no longer match its preview."
            raise CardPreviewError(message)
        self._note.fields = list(fields)

    def variants(self, fields: tuple[str, ...]) -> tuple[CardVariant, ...]:
        """Find existing cards and templates or clozes in the draft.

        Returns:
            The available variants in ordinal order.
        """
        self._set_fields(fields)
        if self._notetype["type"] == MODEL_CLOZE:
            return cloze_variants(self._note.cloze_numbers_in_fields(), self._cards)
        names = tuple(str(template["name"]) for template in self._notetype["tmpls"])
        return standard_variants(names, self._cards)

    def render(self, fields: tuple[str, ...], ordinal: int) -> RenderedCard:
        """Render both sides of one card using the supplied draft fields.

        Returns:
            The rendered question, answer, and any content limitation.

        Raises:
            CardPreviewError: If the selected card template is unavailable.
        """
        self._set_fields(fields)
        template_index = 0 if self._notetype["type"] == MODEL_CLOZE else ordinal
        templates = self._notetype["tmpls"]
        if template_index < 0 or template_index >= len(templates):
            message = "This card's template is unavailable."
            raise CardPreviewError(message)
        template = copy(templates[template_index])
        template["ord"] = ordinal

        card = self._cards.get(ordinal)
        if card is None:
            card = _PreviewCard(self._col, self._note, ordinal, None)
        output = TemplateRenderContext(
            self._col,
            card,
            self._note,
            browser=True,
            notetype=self._notetype,
            template=template,
            fill_empty=False,
        ).render()
        card.set_render_output(output)
        self._rendered_card = card
        notice = ""
        if _LEGACY_LATEX.search(output.question_text) or _LEGACY_LATEX.search(output.answer_text):
            notice = "Legacy LaTeX is not rendered in the live preview."
        return RenderedCard(output.question_and_style(), output.answer_and_style(), notice)

    def play_audio(self, command: str) -> None:
        """Play a valid audio reference from the last rendered card."""
        card = self._rendered_card
        match = _AUDIO_COMMAND.fullmatch(command)
        if card is None or match is None:
            return
        tags = card.question_av_tags() if match[1] == "q" else card.answer_av_tags()
        if int(match[2]) < len(tags):
            play_clicked_audio(command, card)
