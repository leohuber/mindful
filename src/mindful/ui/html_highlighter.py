"""Syntax highlighting for HTML field editors."""

import re
from typing import override

from aqt.qt import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument
from aqt.theme import theme_manager

_TAG = re.compile(r"""</?[A-Za-z][^<>"']*(?:(?:"[^"]*"|'[^']*')[^<>"']*)*>?""")
_TAG_NAME = re.compile(r"^</?[^\s/>]+|/?>$")
_ATTRIBUTE_NAME = re.compile(r"""(?<=\s)[^\s=/>"']+(?=\s*=)""")
_ATTRIBUTE_VALUE = re.compile(r"""=\s*("[^"]*"?|'[^']*'?|[^\s>"']+)""")
_ENTITY = re.compile(r"&(?:#\d+|#[xX][0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);")
_CLOZE = re.compile(r"\{\{c\d+::|::(?=[^{}]*\}\})|\}\}")
_MATHJAX = re.compile(r"\\[()[\]]")
_COMMENT_START = "<!--"
_COMMENT_END = "-->"
_IN_COMMENT = 1
_MAX_BMP_CODE_POINT = 0xFFFF

_LIGHT = {
    "tag": "#1f5fbf",
    "attribute": "#9a4d00",
    "value": "#0a7d32",
    "entity": "#a0208f",
    "cloze": "#c0392b",
    "mathjax": "#6c3fb5",
    "comment": "#7a7a7a",
}
_DARK = {
    "tag": "#7fb4ff",
    "attribute": "#e0a868",
    "value": "#8fd18f",
    "entity": "#e68ae0",
    "cloze": "#ff8a7a",
    "mathjax": "#c3a6ff",
    "comment": "#8c8c8c",
}


def _format(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    text_format = QTextCharFormat()
    text_format.setForeground(QColor(color))
    if bold:
        text_format.setFontWeight(QFont.Weight.Bold)
    text_format.setFontItalic(italic)
    return text_format


class HtmlHighlighter(QSyntaxHighlighter):
    """Colors HTML markup, cloze deletions and MathJax delimiters without changing the text."""

    def __init__(self, document: QTextDocument) -> None:
        """Highlight `document` with colors for the current light or dark theme."""
        super().__init__(document)
        colors = _DARK if theme_manager.night_mode else _LIGHT
        self._formats = {
            "tag": _format(colors["tag"]),
            "attribute": _format(colors["attribute"]),
            "value": _format(colors["value"]),
            "entity": _format(colors["entity"]),
            "cloze": _format(colors["cloze"], bold=True),
            "mathjax": _format(colors["mathjax"], bold=True),
            "comment": _format(colors["comment"], italic=True),
        }
        self._units: list[int] = [0]

    @override
    def highlightBlock(self, text: str | None) -> None:
        text = text or ""
        self._units = [0]
        for character in text:
            self._units.append(self._units[-1] + (2 if ord(character) > _MAX_BMP_CODE_POINT else 1))
        for tag in _TAG.finditer(text):
            offset = tag.start()
            for part in _TAG_NAME.finditer(tag.group()):
                self._apply(offset + part.start(), offset + part.end(), "tag")
            for part in _ATTRIBUTE_NAME.finditer(tag.group()):
                self._apply(offset + part.start(), offset + part.end(), "attribute")
            for part in _ATTRIBUTE_VALUE.finditer(tag.group()):
                self._apply(offset + part.start(1), offset + part.end(1), "value")
        for name, pattern in (("entity", _ENTITY), ("cloze", _CLOZE), ("mathjax", _MATHJAX)):
            for match in pattern.finditer(text):
                self._apply(match.start(), match.end(), name)
        self._highlight_comments(text)

    def _highlight_comments(self, text: str) -> None:
        self.setCurrentBlockState(0)
        continued = self.previousBlockState() == _IN_COMMENT
        start = 0 if continued else text.find(_COMMENT_START)
        while start >= 0:
            end = text.find(_COMMENT_END, start if continued else start + len(_COMMENT_START))
            continued = False
            if end < 0:
                self._apply(start, len(text), "comment")
                self.setCurrentBlockState(_IN_COMMENT)
                return
            end += len(_COMMENT_END)
            self._apply(start, end, "comment")
            start = text.find(_COMMENT_START, end)

    def _apply(self, start: int, end: int, name: str) -> None:
        self.setFormat(self._units[start], self._units[end] - self._units[start], self._formats[name])
