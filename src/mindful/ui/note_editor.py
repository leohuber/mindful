"""Mindful's note editor window."""

import json
import logging
import re
from typing import override

import aqt
from aqt import gui_hooks
from aqt.qt import (
    QButtonGroup,
    QCloseEvent,
    QComboBox,
    QDialogButtonBox,
    QEvent,
    QFont,
    QFontDatabase,
    QHBoxLayout,
    QLabel,
    QObject,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSignalBlocker,
    QSplitter,
    QStackedWidget,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
    qconnect,
)
from aqt.sound import av_refs_to_play_icons
from aqt.theme import theme_manager
from aqt.utils import askUser, restoreGeom, saveGeom, showWarning, tooltip
from aqt.webview import AnkiWebView, AnkiWebViewKind

from ..application.card_preview import CardPreview, CardPreviewError, PreviewController, PreviewSide, RenderedCard
from ..application.note_editing import NoteChangedError, NoteDeletedError, NoteEditing
from ..core.note_draft import NoteDraft

_GEOMETRY_KEY = "mindfulNoteEditor"
_PREVIEW_EDIT_DELAY_MS = 200
_PREVIEW_DISPLAY_TIMEOUT_MS = 15000
_TYPE_ANSWER = re.compile(r"\[\[type:[^]]+\]\]")
_LOGGER = logging.getLogger(__name__)
_HTML_MODE_TOOLTIP = (
    "This field contains markup that Markdown cannot represent without loss, so it is shown and saved exactly as raw HTML.\n\nReason: {reason}"
)
_MARKDOWN_MODE_TOOLTIP = "This field is shown as Markdown and saved back as Anki HTML."


class NoteEditorWindow(QWidget):
    """Non-modal window editing one note's fields as Markdown or raw HTML."""

    def __init__(self, parent: QWidget, editing: NoteEditing, preview: CardPreview) -> None:
        """Create an empty editor that saves through `editing` and previews through `preview`."""
        super().__init__(parent, Qt.WindowType.Window)
        self._editing = editing
        self._preview = PreviewController(preview)
        self._draft: NoteDraft | None = None
        self._editors: list[QPlainTextEdit] = []
        self._saving = False
        self._preview_web: AnkiWebView | None = None
        self._pending_generation: int | None = None
        self._displayed_generation: int | None = None
        self._pending_notice = ""
        self._rendering_preview = False
        self._render_again = False
        self.setWindowTitle("Mindful: Edit Note")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._fields = QWidget()
        self._fields_layout = QVBoxLayout(self._fields)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._fields)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        scroll.setMinimumWidth(200)
        splitter.addWidget(scroll)
        splitter.addWidget(self._create_preview_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        qconnect(self._preview_timer.timeout, self._render_preview)
        self._preview_timeout = QTimer(self)
        self._preview_timeout.setSingleShot(True)
        qconnect(self._preview_timeout.timeout, self._on_preview_timeout)

        buttons = QDialogButtonBox()
        self._save_button = QPushButton("Save")
        self._save_button.setDefault(True)
        buttons.addButton(self._save_button, QDialogButtonBox.ButtonRole.AcceptRole)
        close_button = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        qconnect(self._save_button.clicked, self._save)
        if close_button is not None:
            qconnect(close_button.clicked, self.close)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter, 1)
        layout.addWidget(buttons)
        restoreGeom(self, _GEOMETRY_KEY, default_size=(1050, 600))
        parent.installEventFilter(self)
        self._sync_preview_controls()
        self._update_state()

    def _create_preview_panel(self) -> QWidget:
        preview_panel = QWidget()
        preview_panel.setMinimumWidth(250)
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        card_label = QLabel("Card:")
        self._card_selector = QComboBox()
        card_label.setBuddy(self._card_selector)
        self._front_button = QPushButton("Front")
        self._back_button = QPushButton("Back")
        self._side_group = QButtonGroup(self)
        for button in (self._front_button, self._back_button):
            button.setCheckable(True)
            self._side_group.addButton(button)
        controls.addWidget(card_label)
        controls.addWidget(self._card_selector, 1)
        controls.addWidget(self._front_button)
        controls.addWidget(self._back_button)
        preview_layout.addLayout(controls)

        context_notice = QLabel("Card-specific context and add-on rendering may differ from review.")
        context_notice.setWordWrap(True)
        preview_layout.addWidget(context_notice)
        self._preview_notice = QLabel()
        self._preview_notice.setWordWrap(True)
        self._preview_notice.hide()
        preview_layout.addWidget(self._preview_notice)
        self._preview_stack = QStackedWidget()
        self._preview_status = QLabel("No card preview is available.")
        self._preview_status.setWordWrap(True)
        self._preview_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_stack.addWidget(self._preview_status)
        preview_layout.addWidget(self._preview_stack, 1)

        qconnect(self._card_selector.currentIndexChanged, self._select_preview_card)
        qconnect(self._front_button.clicked, lambda: self._select_preview_side("front"))
        qconnect(self._back_button.clicked, lambda: self._select_preview_side("back"))
        return preview_panel

    @property
    def has_unsaved_changes(self) -> bool:
        """Whether the editor holds edits that have not been saved."""
        return self._draft is not None and self._draft.has_changes

    def confirm_discard(self) -> bool:
        """Ask before discarding unsaved edits.

        Returns:
            True if there are no unsaved edits or the user agreed to discard them.
        """
        if not self.has_unsaved_changes:
            return True
        return askUser("Discard your unsaved changes to this note?", parent=self, defaultno=True, title="Mindful")

    def open_note(self, note_id: int) -> None:
        """Show `note_id`, asking first if unsaved edits of another note would be lost."""
        if self._draft is not None and self._draft.snapshot.note_id == note_id and self.has_unsaved_changes:
            self._raise()
            return
        if self._saving or not self.confirm_discard():
            self._raise()
            return
        try:
            draft = self._editing.open(note_id)
        except NoteDeletedError:
            showWarning("This note no longer exists.", parent=self.parentWidget(), title="Mindful")
            return
        self._show_draft(draft)
        self._raise()

    def _raise(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _show_draft(self, draft: NoteDraft) -> None:
        preserve_selection = self._draft is not None and self._draft.snapshot.note_id == draft.snapshot.note_id
        self._preview_timer.stop()
        self._preview_timeout.stop()
        self._pending_generation = None
        self._displayed_generation = None
        self._draft = draft
        preview_error: Exception | None = None
        try:
            self._preview.open(draft.snapshot, preserve_selection=preserve_selection)
        except CardPreviewError as error:
            preview_error = error
        except Exception as error:
            _LOGGER.exception("Could not open card preview")
            preview_error = error
        while (item := self._fields_layout.takeAt(0)) is not None:
            if (widget := item.widget()) is not None:
                widget.deleteLater()
        self._editors = []
        for index, field in enumerate(draft.fields):
            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(0, 0, 0, 0)
            name = QLabel(field.name)
            font = QFont(name.font())
            font.setBold(True)
            name.setFont(font)
            badge = QLabel("Markdown" if field.mode == "markdown" else "HTML")
            badge.setToolTip(_MARKDOWN_MODE_TOOLTIP if field.mode == "markdown" else _HTML_MODE_TOOLTIP.format(reason=field.reason))
            badge.setStyleSheet("border: 1px solid palette(mid); border-radius: 3px; padding: 0 4px;")
            header_layout.addWidget(name)
            header_layout.addWidget(badge)
            header_layout.addStretch()

            editor = QPlainTextEdit()
            editor.setPlainText(field.text)
            editor.setTabChangesFocus(True)
            if field.mode == "html":
                editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
            qconnect(editor.textChanged, lambda i=index, e=editor: self._on_text_changed(i, e))
            self._fields_layout.addWidget(header)
            self._fields_layout.addWidget(editor)
            self._editors.append(editor)
        self._update_state()
        self._sync_preview_controls()
        if preview_error is None:
            self._request_preview(immediate=True)
        else:
            self._show_preview_error(preview_error)

    def _on_text_changed(self, index: int, editor: QPlainTextEdit) -> None:
        if self._draft is not None and index < len(self._editors) and self._editors[index] is editor:
            self._draft.set_text(index, editor.toPlainText())
            self._request_preview()
        self._update_state()

    def _request_preview(self, *, immediate: bool = False) -> None:
        self._preview.invalidate()
        self._preview_timeout.stop()
        self._pending_generation = None
        self._displayed_generation = None
        self._show_preview_status("Updating preview...")
        self._preview_timer.start(0 if immediate else _PREVIEW_EDIT_DELAY_MS)

    def _sync_preview_controls(self) -> None:
        selection = self._preview.selection
        with QSignalBlocker(self._card_selector):
            self._card_selector.clear()
            for variant in selection.variants:
                label = variant.name if variant.exists else f"{variant.name} (preview only)"
                self._card_selector.addItem(label, variant.ordinal)
            index = self._card_selector.findData(selection.ordinal) if selection.ordinal is not None else -1
            self._card_selector.setCurrentIndex(index)
        available = selection.ordinal is not None
        self._card_selector.setEnabled(available)
        self._front_button.setEnabled(available)
        self._back_button.setEnabled(available)
        self._front_button.setChecked(selection.side == "front")
        self._back_button.setChecked(selection.side == "back")

    def _select_preview_card(self, index: int) -> None:
        ordinal = self._card_selector.itemData(index)
        if not isinstance(ordinal, int) or ordinal == self._preview.selection.ordinal:
            return
        self._preview.selection.select_variant(ordinal)
        self._sync_preview_controls()
        self._request_preview(immediate=True)

    def _select_preview_side(self, side: PreviewSide) -> None:
        if self._preview.selection.ordinal is None or self._preview.selection.side == side:
            return
        self._preview.selection.select_side(side)
        self._sync_preview_controls()
        self._request_preview(immediate=True)

    def _render_preview(self) -> None:
        # Host rendering hooks may run nested event loops, so do not overlap sessions.
        if self._rendering_preview:
            self._render_again = True
            return
        draft = self._draft
        if draft is None:
            return
        generation = self._preview.generation
        self._rendering_preview = True
        try:
            rendered = self._preview.render(draft)
            if not self._preview.is_current(generation):
                return
            self._sync_preview_controls()
            if rendered is None:
                self._show_preview_status("No cards or preview variants are available.")
                return
            self._display_preview(rendered, generation)
        except CardPreviewError as error:
            self._handle_preview_failure(error, generation)
        except Exception as error:
            _LOGGER.exception("Could not render card preview")
            self._handle_preview_failure(error, generation)
        finally:
            self._rendering_preview = False
            if self._render_again:
                self._render_again = False
                if self._draft is not None and not self._preview_timer.isActive():
                    self._preview_timer.start(0)

    def _handle_preview_failure(self, error: Exception, generation: int) -> None:
        if self._preview.is_current(generation):
            self._preview_timeout.stop()
            self._pending_generation = None
            self._displayed_generation = None
            self._sync_preview_controls()
            self._show_preview_error(error)

    def _ensure_preview_web(self) -> AnkiWebView:
        if self._preview_web is not None:
            return self._preview_web
        main_window = aqt.mw
        if main_window is None or main_window.col is None:
            message = "The collection is not open."
            raise CardPreviewError(message)
        web = AnkiWebView(kind=AnkiWebViewKind.PREVIEWER)
        try:
            gui_hooks.card_review_webview_did_init(web, AnkiWebViewKind.PREVIEWER)
            web.set_bridge_command(self._on_preview_command, self)
            web.setPlaybackRequiresGesture(True)
            web.stdHtml(
                main_window.reviewer.revHtml(),
                css=["css/reviewer.css"],
                js=["js/mathjax.js", "js/vendor/mathjax/tex-chtml-full.js", "js/reviewer.js"],
                context=self,
            )
        except Exception:
            web.cleanup()
            web.deleteLater()
            raise
        self._preview_stack.addWidget(web)
        self._preview_web = web
        return web

    def _display_preview(self, rendered: RenderedCard, generation: int) -> None:
        main_window = aqt.mw
        if main_window is None or main_window.col is None:
            message = "The collection is not open."
            raise CardPreviewError(message)
        media = main_window.col.media
        question = av_refs_to_play_icons(media.escape_media_filenames(_TYPE_ANSWER.sub("", rendered.question)))
        answer = av_refs_to_play_icons(media.escape_media_filenames(_TYPE_ANSWER.sub("", rendered.answer)))
        ordinal = self._preview.selection.ordinal
        if ordinal is None:
            return
        body_class = theme_manager.body_classes_for_card_ord(ordinal)
        if self._preview.selection.side == "front":
            answer_for_front = media.escape_media_filenames(rendered.answer)
            show = f"_showQuestion({json.dumps(question)}, {json.dumps(answer_for_front)}, {json.dumps(body_class)});"
        else:
            show = f"_showAnswer({json.dumps(answer)}, {json.dumps(body_class)});"
        web = self._ensure_preview_web()
        self._pending_generation = generation
        self._pending_notice = rendered.notice
        self._preview_timeout.start(_PREVIEW_DISPLAY_TIMEOUT_MS)
        ready = json.dumps(f"mindful-preview-ready:{generation}")
        failure = json.dumps(f"mindful-preview-error:{generation}")
        web.eval(f"try {{ {show} _queueAction(() => pycmd({ready})); }} catch (error) {{ pycmd({failure}); }}")

    def _on_preview_command(self, command: str) -> None:
        if command.startswith("play:"):
            if self._displayed_generation is not None and self._preview.is_current(self._displayed_generation):
                try:
                    self._preview.play_audio(command)
                except Exception:
                    _LOGGER.exception("Could not play card preview audio")
                    self._preview_notice.setText("Audio could not be played.")
                    self._preview_notice.show()
            return
        for prefix, success in (("mindful-preview-ready:", True), ("mindful-preview-error:", False)):
            if command.startswith(prefix):
                try:
                    generation = int(command.removeprefix(prefix))
                except ValueError:
                    return
                if generation != self._pending_generation or not self._preview.is_current(generation):
                    return
                self._preview_timeout.stop()
                self._pending_generation = None
                if success and self._preview_web is not None:
                    self._displayed_generation = generation
                    self._preview_notice.setText(self._pending_notice)
                    self._preview_notice.setVisible(bool(self._pending_notice))
                    self._preview_stack.setCurrentWidget(self._preview_web)
                else:
                    self._show_preview_status("Preview unavailable: the card could not be displayed.")
                return

    def _on_preview_timeout(self) -> None:
        generation = self._pending_generation
        if generation is not None and self._preview.is_current(generation):
            self._pending_generation = None
            self._show_preview_status("Preview unavailable: the card took too long to display.")

    def _show_preview_status(self, message: str) -> None:
        self._preview_notice.hide()
        self._preview_status.setText(message)
        self._preview_stack.setCurrentWidget(self._preview_status)

    def _show_preview_error(self, error: Exception) -> None:
        detail = str(error) or "the card could not be rendered."
        self._show_preview_status(f"Preview unavailable: {detail}")

    def _update_state(self) -> None:
        self._save_button.setEnabled(self.has_unsaved_changes and not self._saving)
        for editor in self._editors:
            editor.setReadOnly(self._saving)
        marker = " *" if self.has_unsaved_changes else ""
        self.setWindowTitle(f"Mindful: Edit Note{marker}")

    def _save(self) -> None:
        if self._draft is None or not self.has_unsaved_changes or self._saving:
            return
        self._saving = True
        self._update_state()
        self._editing.save(self._draft, self._on_saved, self._on_save_failed)

    def _on_saved(self, draft: NoteDraft) -> None:
        self._saving = False
        self._show_draft(draft)
        tooltip("Note saved.", parent=self)

    def _on_save_failed(self, error: Exception) -> None:
        self._saving = False
        self._update_state()
        if isinstance(error, NoteChangedError):
            message = (
                "This note was changed elsewhere after you opened it, so nothing was saved.\n\n"
                "Your edits are still in the editor. Copy them if needed, then reopen the note."
            )
        elif isinstance(error, NoteDeletedError):
            message = "This note no longer exists, so nothing was saved."
        else:
            message = f"The note could not be saved: {error}"
        showWarning(message, parent=self, title="Mindful")

    @override
    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Ask before discarding unsaved edits when the window closes."""
        if event is None:
            return
        if self._saving or not self.confirm_discard():
            event.ignore()
            return
        self._discard_and_close(event)

    def _discard_and_close(self, event: QCloseEvent) -> None:
        self._preview_timer.stop()
        self._preview_timeout.stop()
        self._pending_generation = None
        self._displayed_generation = None
        self._render_again = False
        self._draft = None
        self._preview.close()
        if self._preview_web is not None:
            try:
                self._preview_web.cleanup()
            except Exception:
                _LOGGER.exception("Could not clean up card preview")
            self._preview_web = None
        saveGeom(self, _GEOMETRY_KEY)
        parent = self.parentWidget()
        if parent is not None:
            parent.removeEventFilter(self)
        event.accept()

    @override
    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        """Ask before the owning Browser closes over unsaved edits.

        Returns:
            True to stop the Browser from closing.
        """
        if watched is self.parentWidget() and event is not None and event.type() == QEvent.Type.Close:
            cleaned_up = bool(getattr(watched, "_closeEventHasCleanedUp", False))
            if not cleaned_up and (self._saving or not self.confirm_discard()):
                event.ignore()
                return True
            self._draft = None
            self.close()
        return False
