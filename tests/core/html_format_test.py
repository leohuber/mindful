import pytest

from mindful.core.html_format import MAX_FORMATTED_LENGTH, compact_html, format_html


def test_block_and_list_markup_starts_lines_and_indents_items() -> None:
    assert format_html("<div>One</div><ul><li>A</li><li>B</li></ul>") == "<div>One</div>\n<ul>\n  <li>A</li>\n  <li>B</li>\n</ul>"


def test_line_breaks_continue_on_a_new_line() -> None:
    assert format_html("one<br>two<br/>three") == "one<br>\ntwo<br/>\nthree"


@pytest.mark.parametrize(
    "html",
    [
        "<p><b>a</b><i>b</i></p>",
        '<span class="hint">{{c1::answer::hint}}</span>',
        "\\(x_1^2\\) and [sound:clip_one.mp3]",
        '<img src="cat.jpg">',
    ],
)
def test_inline_content_stays_on_one_line(html: str) -> None:
    assert format_html(html) == html


def test_whitespace_sensitive_elements_are_untouched() -> None:
    formatted = format_html("<pre>a<div>b</div></pre><div>c</div>")

    assert formatted == "<pre>a<div>b</div></pre>\n<div>c</div>"


@pytest.mark.parametrize(
    "html",
    [
        "",
        "plain",
        "<table><tr><td>1</td><td>2</td></tr></table>",
        "A <ul><li>x</li></ul>",
        '<span title="a>b">x</span><div>y</div>',
        "<!-- note --><div>x</div>",
        "<div>unclosed<p>x",
        "<li>A<ul><li>{{c1::x}}</li></ul></li>",
        "<style>div{color:red}</style><div>x</div>",
    ],
)
def test_compacting_formatted_html_restores_the_original(html: str) -> None:
    formatted = format_html(html)

    assert formatted is not None
    assert compact_html(formatted) == html


@pytest.mark.parametrize("html", ["<div>a</div>\n<div>b</div>", "line<br>\n  next", "x" * (MAX_FORMATTED_LENGTH + 1)])
def test_html_that_cannot_round_trip_is_not_formatted(html: str) -> None:
    assert format_html(html) is None


def test_compacting_keeps_spaces_and_whitespace_inside_inline_text() -> None:
    assert compact_html("<div>a b</div>\n  <b>x</b> <i>y</i>\n<pre>\n keep\n</pre>") == "<div>a b</div><b>x</b> <i>y</i><pre>\n keep\n</pre>"


def test_compacting_keeps_newlines_between_inline_elements() -> None:
    assert compact_html("<b>a</b>\n<i>b</i>") == "<b>a</b>\n<i>b</i>"
