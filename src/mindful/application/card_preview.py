"""Host-independent contracts and selection state for card previews."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol

from ..core.note_draft import NoteDraft, NoteSnapshot

PreviewSide = Literal["front", "back"]


@dataclass(frozen=True)
class CardVariant:
    """A card or template that can be previewed."""

    ordinal: int
    name: str
    exists: bool


@dataclass(frozen=True)
class RenderedCard:
    """The rendered sides of a card and any preview-specific notice."""

    question: str
    answer: str
    notice: str = ""


class PreviewSession(Protocol):
    """Preview one note without saving it."""

    def variants(self, fields: tuple[str, ...]) -> tuple[CardVariant, ...]:
        """Find the cards and preview-only variants represented by `fields`."""
        ...

    def render(self, fields: tuple[str, ...], ordinal: int) -> RenderedCard:
        """Render both sides of the selected variant using `fields`."""
        ...

    def play_audio(self, command: str) -> None:
        """Play audio requested by the current rendered card."""
        ...


class CardPreview(Protocol):
    """Open a preview session for a note snapshot."""

    def open(self, expected: NoteSnapshot) -> PreviewSession:
        """Bind a read-only preview session to the opened note snapshot."""
        ...


class CardPreviewError(Exception):
    """A card preview cannot be opened or rendered."""


def standard_variants(template_names: tuple[str, ...], existing_ordinals: Iterable[int]) -> tuple[CardVariant, ...]:
    """Combine note-type templates with existing card ordinals.

    Returns:
        Variants in ordinal order, including existing cards with missing templates.
    """
    existing = set(existing_ordinals)
    names = dict(enumerate(template_names))
    for ordinal in existing:
        names.setdefault(ordinal, f"Card {ordinal + 1}")
    return tuple(CardVariant(ordinal, names[ordinal], ordinal in existing) for ordinal in sorted(names))


def cloze_variants(cloze_numbers: Iterable[int], existing_ordinals: Iterable[int]) -> tuple[CardVariant, ...]:
    """Combine draft cloze numbers with existing card ordinals.

    Returns:
        Variants in ordinal order, including existing cards without a draft cloze.
    """
    existing = set(existing_ordinals)
    ordinals = existing | {number - 1 for number in cloze_numbers if number > 0}
    return tuple(CardVariant(ordinal, f"Cloze {ordinal + 1}", ordinal in existing) for ordinal in sorted(ordinals))


class PreviewSelection:
    """Keep the selected card and side stable as variants change."""

    def __init__(self) -> None:
        """Start with no selectable cards."""
        self.variants: tuple[CardVariant, ...] = ()
        self.ordinal: int | None = None
        self.side: PreviewSide = "back"

    def update_variants(self, variants: tuple[CardVariant, ...]) -> None:
        """Replace available variants, keeping the selection when possible."""
        self.variants = variants
        if self.ordinal is not None and any(variant.ordinal == self.ordinal for variant in variants):
            return
        first = next((variant for variant in variants if variant.exists), None)
        if first is None and variants:
            first = variants[0]
        self.ordinal = first.ordinal if first is not None else None
        self.side = "back"

    def select_variant(self, ordinal: int) -> None:
        """Select an available variant, showing its front.

        Raises:
            ValueError: If the variant is not available.
        """
        if not any(variant.ordinal == ordinal for variant in self.variants):
            raise ValueError(ordinal)
        if self.ordinal != ordinal:
            self.ordinal = ordinal
            self.side = "back"

    def select_side(self, side: PreviewSide) -> None:
        """Choose the front or back of the selected card."""
        self.side = side


class PreviewController:
    """Coordinate a draft with a read-only preview session."""

    def __init__(self, preview: CardPreview) -> None:
        """Use `preview` to open host-specific sessions."""
        self._preview = preview
        self._snapshot: NoteSnapshot | None = None
        self._session: PreviewSession | None = None
        self._generation = 0
        self.selection = PreviewSelection()

    @property
    def generation(self) -> int:
        """Identify the latest requested preview state."""
        return self._generation

    def invalidate(self) -> None:
        """Reject results requested before the current editor state."""
        self._generation += 1

    def is_current(self, generation: int) -> bool:
        """Check whether a deferred result still belongs to the open note.

        Returns:
            True if the note is open and the result is current.
        """
        return self._snapshot is not None and generation == self._generation

    def open(self, snapshot: NoteSnapshot, *, preserve_selection: bool = False) -> None:
        """Open `snapshot` for preview, replacing any previous session."""
        if not preserve_selection or self._snapshot is None or self._snapshot.note_id != snapshot.note_id:
            self.selection = PreviewSelection()
        self.invalidate()
        self._snapshot = snapshot
        self._session = None
        generation = self._generation
        session = self._preview.open(snapshot)
        if self.is_current(generation):
            self._session = session

    def render(self, draft: NoteDraft) -> RenderedCard | None:
        """Render the selected variant of `draft`, if one is available.

        Returns:
            The rendered card, or None when no variant is available.

        Raises:
            CardPreviewError: If a preview session is unavailable.
        """
        if self._snapshot != draft.snapshot:
            self.open(draft.snapshot, preserve_selection=True)
        generation = self._generation
        if self._snapshot != draft.snapshot:
            return None
        if self._session is None:
            session = self._preview.open(draft.snapshot)
            if not self.is_current(generation):
                return None
            self._session = session
        session = self._session
        if session is None:
            raise CardPreviewError
        fields = draft.preview_html()
        variants = session.variants(fields)
        if not self.is_current(generation):
            return None
        self.selection.update_variants(variants)
        if self.selection.ordinal is None:
            return None
        rendered = session.render(fields, self.selection.ordinal)
        return rendered if self.is_current(generation) else None

    def play_audio(self, command: str) -> None:
        """Forward a playback request for the currently rendered card."""
        if self._session is not None:
            self._session.play_audio(command)

    def close(self) -> None:
        """Discard the preview session and invalidate outstanding results."""
        self.invalidate()
        self._snapshot = None
        self._session = None
        self.selection = PreviewSelection()
