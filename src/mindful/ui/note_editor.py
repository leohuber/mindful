"""Mindful's note editor window."""

from typing import override

from aqt.qt import (
    QCloseEvent,
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
    Qt,
    QVBoxLayout,
    QWidget,
    qconnect,
)
from aqt.utils import askUser, restoreGeom, saveGeom, showWarning, tooltip

from ..application.note_editing import NoteChangedError, NoteDeletedError, NoteEditing
from ..core.note_draft import NoteDraft

_GEOMETRY_KEY = "mindfulNoteEditor"
_HTML_MODE_TOOLTIP = (
    "This field contains markup that Markdown cannot represent without loss, so it is shown and saved exactly as raw HTML.\n\nReason: {reason}"
)
_MARKDOWN_MODE_TOOLTIP = "This field is shown as Markdown and saved back as Anki HTML."


class NoteEditorWindow(QWidget):
    """Non-modal window editing one note's fields as Markdown or raw HTML."""

    def __init__(self, parent: QWidget, editing: NoteEditing) -> None:
        """Create an empty editor owned by `parent`, saving through `editing`."""
        super().__init__(parent, Qt.WindowType.Window)
        self._editing = editing
        self._draft: NoteDraft | None = None
        self._editors: list[QPlainTextEdit] = []
        self._saving = False
        self.setWindowTitle("Mindful: Edit Note")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._fields = QWidget()
        self._fields_layout = QVBoxLayout(self._fields)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._fields)

        buttons = QDialogButtonBox()
        self._save_button = QPushButton("Save")
        self._save_button.setDefault(True)
        buttons.addButton(self._save_button, QDialogButtonBox.ButtonRole.AcceptRole)
        close_button = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        qconnect(self._save_button.clicked, self._save)
        if close_button is not None:
            qconnect(close_button.clicked, self.close)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttons)
        restoreGeom(self, _GEOMETRY_KEY, default_size=(700, 600))
        parent.installEventFilter(self)
        self._update_state()

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
        self._draft = draft
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

    def _on_text_changed(self, index: int, editor: QPlainTextEdit) -> None:
        if self._draft is not None:
            self._draft.set_text(index, editor.toPlainText())
        self._update_state()

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
        self._draft = None
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
