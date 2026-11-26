"""Composition root for Anki integrations."""

from aqt import mw

from .application.note_editing import NoteEditing
from .core.editor_settings import resolve_field_font_size
from .core.shortcuts import resolve_edit_note_shortcut
from .integration.card_preview import CollectionCardPreview
from .integration.note_store import CollectionNoteStore
from .ui.browser_action import BrowserNoteAction

_ADDON_MODULE = __name__.split(".", maxsplit=1)[0]


def initialize() -> None:
    """Initialize host integrations when Anki is running."""
    if mw is None:
        return
    main_window = mw
    editing = NoteEditing(CollectionNoteStore(main_window))
    preview = CollectionCardPreview(main_window)

    def config() -> object:
        return main_window.addonManager.getConfig(_ADDON_MODULE)

    BrowserNoteAction(
        editing,
        preview,
        lambda: resolve_edit_note_shortcut(config()),
        lambda: resolve_field_font_size(config()),
    ).register()
