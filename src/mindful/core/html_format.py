"""Format field HTML for reading and compact it again for storage."""

import re
from dataclasses import dataclass
from typing import Literal

MAX_FORMATTED_LENGTH = 100_000

_TOKEN = re.compile(
    r"<!--.*?-->"
    r"|<[!?][^>]*>"
    r"|<(?P<close>/?)(?P<name>[A-Za-z][A-Za-z0-9-]*)(?:[^>\"']|\"[^\"]*\"|'[^']*')*>",
    re.DOTALL,
)
_BLOCK = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "details",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
_VOID_BLOCK = frozenset({"hr"})
_PROTECTED = frozenset({"code", "pre", "script", "style", "textarea"})
_INDENT = "  "
_LEADING_SPACE = re.compile(r"^\s+")
_TRAILING_SPACE = re.compile(r"\s+$")


@dataclass(frozen=True)
class _Token:
    kind: Literal["text", "tag", "other"]
    raw: str
    name: str = ""
    closing: bool = False

    @property
    def self_closing(self) -> bool:
        return self.raw.endswith("/>")

    @property
    def is_block(self) -> bool:
        return self.kind == "tag" and self.name in _BLOCK

    @property
    def is_line_break(self) -> bool:
        return self.kind == "tag" and self.name == "br" and not self.closing


def _tokenize(html: str) -> list[_Token]:
    tokens: list[_Token] = []
    position = 0
    for match in _TOKEN.finditer(html):
        if match.start() > position:
            tokens.append(_Token("text", html[position : match.start()]))
        if (name := match.group("name")) is not None:
            tokens.append(_Token("tag", match.group(), name.lower(), bool(match.group("close"))))
        else:
            tokens.append(_Token("other", match.group()))
        position = match.end()
    if position < len(html):
        tokens.append(_Token("text", html[position:]))
    return tokens


class _ProtectedTracker:
    """Track whether the current position is inside whitespace-sensitive content."""

    def __init__(self) -> None:
        self._open: str | None = None

    @property
    def active(self) -> bool:
        return self._open is not None

    def advance(self, token: _Token) -> None:
        if token.kind != "tag":
            return
        if self._open is None:
            if token.name in _PROTECTED and not token.closing and not token.self_closing:
                self._open = token.name
        elif token.closing and token.name == self._open:
            self._open = None


def _is_boundary(before: _Token, after: _Token) -> bool:
    # Newlines here do not affect how blocks render.
    return before.is_block or before.is_line_break or after.is_block


def _breaks_between(before: _Token, after: _Token) -> bool:
    if not _is_boundary(before, after):
        return False
    if (before.kind == "text" and before.raw[-1:].isspace()) or (after.kind == "text" and after.raw[:1].isspace()):
        return False
    starts_block = after.is_block and not after.closing
    ends_block = before.is_block and (before.closing or before.name in _VOID_BLOCK)
    nested_close = before.is_block and before.closing and after.is_block and after.closing
    return starts_block or ends_block or before.is_line_break or nested_close


def _indented_format(tokens: list[_Token]) -> str:
    parts: list[str] = []
    stack: list[str] = []
    protected = _ProtectedTracker()
    previous: _Token | None = None
    for token in tokens:
        if previous is not None and not protected.active and _breaks_between(previous, token):
            depth = len(stack) - 1 if token.is_block and token.closing and token.name in stack else len(stack)
            parts.append("\n" + _INDENT * max(depth, 0))
        parts.append(token.raw)
        protected.advance(token)
        if token.is_block and not token.self_closing and token.name not in _VOID_BLOCK:
            if not token.closing:
                stack.append(token.name)
            elif token.name in stack:
                del stack[len(stack) - 1 - stack[::-1].index(token.name) :]
        previous = token
    return "".join(parts)


def compact_html(text: str) -> str:
    """Remove line breaks and indentation at block-level boundaries.

    Only whitespace runs containing a newline are removed, and never inside
    `pre`, `code`, `textarea`, `script`, or `style` elements.

    Returns:
        The HTML to store for `text`.
    """
    tokens = _tokenize(text)
    parts: list[str] = []
    protected = _ProtectedTracker()
    for index, token in enumerate(tokens):
        raw = token.raw
        if token.kind == "text" and not protected.active:
            before = tokens[index - 1] if index > 0 else None
            after = tokens[index + 1] if index + 1 < len(tokens) else None
            if raw.isspace():
                if before is not None and after is not None and "\n" in raw and _is_boundary(before, after):
                    raw = ""
            else:
                if before is not None and (before.is_block or before.is_line_break):
                    raw = _LEADING_SPACE.sub(lambda match: "" if "\n" in match.group() else match.group(), raw, count=1)
                if after is not None and after.is_block:
                    raw = _TRAILING_SPACE.sub(lambda match: "" if "\n" in match.group() else match.group(), raw, count=1)
        parts.append(raw)
        protected.advance(token)
    return "".join(parts)


def format_html(html: str) -> str | None:
    """Add line breaks and indentation that compacting removes again.

    Returns:
        Readable text for `html`, or None when `html` cannot be restored exactly from it.
    """
    if len(html) > MAX_FORMATTED_LENGTH:
        return None
    formatted = _indented_format(_tokenize(html))
    return formatted if compact_html(formatted) == html else None
