import pytest

from mindful.core.markdown_fields import (
    UnsupportedMarkupError,
    canonical_html,
    field_presentation,
    html_to_markdown,
    markdown_to_html,
)


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("plain text", "plain text"),
        ("<b>bold</b> <strong>strong</strong>", "**bold** **strong**"),
        ("<i>italic</i> <em>em</em>", "*italic* *em*"),
        ("<code>code</code>", "`code`"),
        ('<a href="https://example.com">link</a>', "[link](https://example.com)"),
        ('<img src="pic.png">', "![](pic.png)"),
        ("<ul><li>one</li><li>two</li></ul>", "- one\n- two"),
        ("<ol><li>one</li><li>two</li></ol>", "1. one\n2. two"),
        ("one<br>two", "one\ntwo"),
        ("one<div>two</div>", "one\ntwo"),
        ("<p>one</p><p>two</p>", "one\n\ntwo"),
    ],
)
def test_html_to_markdown_supports_subset(html: str, expected: str) -> None:
    assert html_to_markdown(html) == expected


@pytest.mark.parametrize(
    "html",
    [
        "<span>text</span>",
        '<b style="color:red">text</b>',
        "<table><tr><td>text</td></tr></table>",
        "<u>text</u>",
        '<a href="url" class="link">text</a>',
        "<a>text</a>",
    ],
)
def test_html_to_markdown_rejects_unsupported_markup(html: str) -> None:
    with pytest.raises(UnsupportedMarkupError):
        html_to_markdown(html)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("one", "one"),
        ("one\n\ntwo", "one<br><br>two"),
        ("one\ntwo", "one<br>two"),
        ("**bold** and *italic*", "<b>bold</b> and <i>italic</i>"),
        ("- one\n- two", "<ul>\n<li>one</li>\n<li>two</li>\n</ul>"),
        ("1. one\n2. two", "<ol>\n<li>one</li>\n<li>two</li>\n</ol>"),
        ("[link](https://example.com)", '<a href="https://example.com">link</a>'),
        ("![alt](pic.png)", '<img alt="alt" src="pic.png">'),
    ],
)
def test_markdown_to_html_uses_anki_style(text: str, expected: str) -> None:
    assert markdown_to_html(text) == expected


@pytest.mark.parametrize(
    "token",
    [r"\(x_1^2\)", r"\[x_1^2\]", "[sound:clip_one.mp3]", "{{c1::answer::hint}}"],
)
def test_anki_tokens_round_trip_next_to_emphasis(token: str) -> None:
    html = f"<b>bold</b>{token}<i>italic</i>"
    text = html_to_markdown(html)
    assert token in text
    assert markdown_to_html(text) == html


def test_token_placeholders_do_not_collide_with_field_text() -> None:
    html = "\ue0000\ue001" + r"\(x_1^2\)"
    assert markdown_to_html(html_to_markdown(html)) == html


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("<strong>bold</strong>", "<b>bold</b>"),
        ("<em>italic</em>", "<i>italic</i>"),
        ("one<div>two</div>", "one<br>two"),
        ("<div>one</div><div>two</div>", "one<br>two"),
        ("<p>one</p><p>two</p>", "one<br><br>two"),
        ("one   two", "one two"),
    ],
)
def test_equivalent_html_has_same_canonical_form(left: str, right: str) -> None:
    assert canonical_html(left) == canonical_html(right)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("one", "two"),
        ('<a href="one">link</a>', '<a href="two">link</a>'),
        ('<img src="one">', '<img src="two">'),
        ("one<br>two", "one<br><br>two"),
        ("a b", "ab"),
        ("<b>one</b> <i>two</i>", "<b>one</b><i>two</i>"),
    ],
)
def test_different_html_has_different_canonical_form(left: str, right: str) -> None:
    assert canonical_html(left) != canonical_html(right)


@pytest.mark.parametrize("html", ["", "one<div>two</div>", "<b>bold</b>", '<img src="pic.png">'])
def test_lossless_fields_use_markdown_mode(html: str) -> None:
    assert field_presentation(html).mode == "markdown"


@pytest.mark.parametrize("html", ['<span style="color:red">text</span>', "<b> bold </b>"])
def test_unsupported_or_lossy_fields_use_exact_html(html: str) -> None:
    result = field_presentation(html)
    assert result.mode == "html"
    assert result.text == html
    assert result.reason


def test_combined_formatting_and_list_is_shown_as_markdown() -> None:
    html = '<b>Bold</b> <i>Italic</i><br><ul><li>one</li><li>two</li></ul><br><a href="https://example.com">link</a>'
    result = field_presentation(html)
    assert result.mode == "markdown"
    assert canonical_html(markdown_to_html(result.text)) == canonical_html(html)
