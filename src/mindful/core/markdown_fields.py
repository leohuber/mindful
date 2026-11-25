"""Convert the supported subset of Anki field HTML to Markdown."""

import re
from dataclasses import dataclass
from html import escape
from typing import Literal

import markdown
from bs4 import BeautifulSoup, Comment, NavigableString, Tag


class UnsupportedMarkupError(ValueError):
    """The field contains HTML that the converter cannot represent safely."""


_INLINE = {"b", "strong", "i", "em", "code", "a", "img"}
_ALLOWED = _INLINE | {"ul", "ol", "li", "br", "div", "p"}
_ATTRIBUTES = {"a": {"href"}, "img": {"src", "alt"}}
_ANKI_TOKEN = re.compile(r"\\\(.*?\\\)|\\\[.*?\\\]|\[sound:[^\]]*\]", re.DOTALL)


def _protect_tokens(text: str) -> tuple[str, dict[str, str]]:
    prefix = "\ue000"
    while prefix in text:
        prefix += "\ue000"
    tokens: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        placeholder = f"{prefix}{len(tokens)}\ue001"
        tokens[placeholder] = match.group()
        return placeholder

    return _ANKI_TOKEN.sub(replace, text), tokens


def _restore_tokens(text: str, tokens: dict[str, str]) -> str:
    for placeholder, original in tokens.items():
        text = text.replace(placeholder, original)
    return text


def _escape_text(text: str) -> str:
    return re.sub(r"([\\`*_\[\]<>#!])", r"\\\1", text)


def _validate_tag(node: Tag) -> None:
    name = node.name
    if name not in _ALLOWED:
        reason = f"unsupported element: {name}"
        raise UnsupportedMarkupError(reason)
    allowed_attributes = _ATTRIBUTES.get(name, set())
    if set(node.attrs) - allowed_attributes:
        reason = f"unsupported attribute on: {name}"
        raise UnsupportedMarkupError(reason)
    if name in {"a", "img"} and not node.has_attr("href" if name == "a" else "src"):
        reason = f"missing required attribute on: {name}"
        raise UnsupportedMarkupError(reason)


def _convert_list(node: Tag, depth: int) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString) and not str(child).strip():
            continue
        if not isinstance(child, Tag) or child.name != "li":
            reason = f"unsupported content in: {node.name}"
            raise UnsupportedMarkupError(reason)
        marker = f"{len(parts) + 1}." if node.name == "ol" else "-"
        parts.append(f"{'    ' * depth}{marker} {_convert(child, depth=depth)}")
    return "\n".join(parts)


def _convert_item(node: Tag, depth: int) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, Tag) and child.name in {"ul", "ol"}:
            parts.append("\n" + _convert(child, depth=depth + 1))
        else:
            parts.append(_convert(child, depth=depth))
    return "".join(parts)


def _convert_inline(node: Tag, depth: int) -> str:
    name = node.name
    content = "".join(_convert(child, depth=depth) for child in node.children)
    if name in {"b", "strong"}:
        return f"**{content}**"
    if name in {"i", "em"}:
        return f"*{content}*"
    if name == "code":
        ticks = "`" * (max((len(match) for match in re.findall(r"`+", node.get_text())), default=0) + 1)
        return f"{ticks}{node.get_text()}{ticks}"
    if name == "a":
        return f"[{content}]({node['href']})"
    return content


def _convert(node: Tag | NavigableString, *, depth: int = 0) -> str:
    if isinstance(node, Comment):
        reason = "HTML comments are unsupported"
        raise UnsupportedMarkupError(reason)
    if isinstance(node, NavigableString):
        return _escape_text(str(node))
    _validate_tag(node)
    if node.name in {"ul", "ol", "li"}:
        return _convert_item(node, depth) if node.name == "li" else _convert_list(node, depth)
    if node.name == "br":
        return "\n"
    if node.name == "img":
        alt = _escape_text(str(node.get("alt", "")))
        return f"![{alt}]({node['src']})"
    content = _convert_inline(node, depth)
    if node.name in {"div", "p"}:
        content = ("\n" if node.name == "div" else "\n\n") + content
    return content


def html_to_markdown(html: str) -> str:
    """Convert supported HTML to Markdown, rejecting unsupported markup.

    Returns:
        The Markdown representation of the field.
    """
    protected, tokens = _protect_tokens(html)
    soup = BeautifulSoup(protected, "html.parser")
    children = list(soup.children)
    parts = []
    for index, child in enumerate(children):
        is_list = isinstance(child, Tag) and child.name in {"ul", "ol"}
        adjacent_list = any(
            0 <= neighbor < len(children) and isinstance(children[neighbor], Tag) and children[neighbor].name in {"ul", "ol"}
            for neighbor in (index - 1, index + 1)
        )
        if isinstance(child, Tag) and child.name == "br" and (adjacent_list or index in {0, len(children) - 1}):
            _validate_tag(child)
            parts.append("<br>")
        elif is_list:
            parts.append(f"\n\n{_convert(child)}\n\n")
        else:
            parts.append(_convert(child))
    result = "".join(parts).strip("\n")
    return _restore_tokens(result, tokens)


def markdown_to_html(text: str) -> str:
    """Render Markdown as Anki-style HTML.

    Returns:
        The rendered HTML field.
    """
    protected, tokens = _protect_tokens(text)
    rendered = markdown.markdown(protected, extensions=["nl2br", "sane_lists"])
    soup = BeautifulSoup(rendered, "html.parser")
    for tag in soup.find_all(["strong", "em"]):
        tag.name = "b" if tag.name == "strong" else "i"

    parts = []
    previous_paragraph = False
    for node in soup.children:
        if isinstance(node, NavigableString) and not str(node).strip():
            continue
        is_paragraph = isinstance(node, Tag) and node.name == "p"
        if is_paragraph:
            if previous_paragraph:
                parts.append("<br><br>")
            parts.append(node.decode_contents())
        else:
            parts.append(str(node))
        previous_paragraph = is_paragraph
    html = re.sub(r"<(br|img)([^>]*)/>", r"<\1\2>", "".join(parts))
    return _restore_tokens(html.replace("<br>\n", "<br>"), tokens)


def _canonical_children(node: Tag | BeautifulSoup) -> str:
    parts: list[str] = []
    previous_block = ""
    for child in node.children:
        if isinstance(child, NavigableString):
            text = re.sub(r"\s+", " ", str(child))
            if not text.strip() and node.name in {"ul", "ol"}:
                continue
            rendered = escape(text)
            block = ""
        else:
            block = child.name if child.name in {"div", "p"} else ""
            rendered = _canonical_tag(child)
        if not rendered:
            continue
        if parts and (block or previous_block):
            count = 2 if "p" in {block, previous_block} else 1
            if not parts[-1].endswith("<br>"):
                parts.append("<br>" * count)
        parts.append(rendered)
        previous_block = block
    return "".join(parts)


def _canonical_tag(tag: Tag) -> str:
    if tag.name == "br":
        return "<br>"
    if tag.name in {"div", "p"}:
        return _canonical_children(tag)
    name = {"strong": "b", "em": "i"}.get(tag.name, tag.name)
    attrs = dict(tag.attrs)
    if name == "img" and attrs.get("alt", "") == "":
        attrs.pop("alt", None)
    attributes = repr(sorted(attrs.items()))
    return f"<{name}{attributes}>{_canonical_children(tag)}</{name}>"


def canonical_html(html: str) -> str:
    """Canonicalize interchangeable HTML for conservative fidelity comparison.

    Returns:
        A canonical representation preserving text, formatting and attributes.
    """
    protected, tokens = _protect_tokens(html)
    soup = BeautifulSoup(protected, "html.parser")
    result = _canonical_children(soup)
    result = re.sub(r" *<br> *", "<br>", result).strip()
    return _restore_tokens(result, tokens)


@dataclass(frozen=True)
class FieldPresentation:
    """Editor text and mode chosen for a stored field."""

    mode: Literal["markdown", "html"]
    text: str
    reason: str = ""


def field_presentation(html: str) -> FieldPresentation:
    """Choose Markdown only when the supported conversion is lossless.

    Returns:
        The editor representation and an explanation for HTML fallback.
    """
    try:
        text = html_to_markdown(html)
    except UnsupportedMarkupError as error:
        return FieldPresentation("html", html, str(error))
    if canonical_html(html) != canonical_html(markdown_to_html(text)):
        return FieldPresentation("html", html, "Markdown round trip changes the field")
    return FieldPresentation("markdown", text)
