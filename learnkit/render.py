"""Render Markdown and code to HTML with Pygments.

The app bundle and the PDF handbook both use this module, so they highlight code
the same way.
"""

from __future__ import annotations

import re

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

LEXERS = {
    "python": "python",
    "pyspark": "python",
    "sql": "sql",
    "tsql": "tsql",
    "kql": "kql",
    "dax": "dax",
    "yaml": "yaml",
    "text": "text",
}
CSS_CLASS = "hl"


ALLOWED_TAGS = frozenset(
    {
        "p",
        "ul",
        "ol",
        "li",
        "a",
        "code",
        "div",
        "pre",
        "span",
        "table",
        "thead",
        "tbody",
        "tr",
        "td",
        "th",
        "strong",
        "em",
        "br",
        "blockquote",
        "hr",
        "h1",
        "h2",
        "h3",
        "h4",
    }
)
_TAG = re.compile(r"<([a-zA-Z][\w-]*)")


def md_to_html(text: str) -> str:
    """Render lesson Markdown (paragraphs, lists, tables, fenced code) to HTML.

    Raw HTML in the source is escaped, not passed through: text such as
    `/Workspace/Users/<email>/` must show as written.
    """
    md = markdown.Markdown(
        extensions=["fenced_code", "codehilite", "tables", "sane_lists"],
        extension_configs={"codehilite": {"css_class": CSS_CLASS, "guess_lang": False}},
        output_format="html",
    )
    md.preprocessors.deregister("html_block")
    md.inlinePatterns.deregister("html")
    return md.convert(text)


def unknown_tags(html: str) -> set[str]:
    """Tag names in rendered HTML that lesson content should never produce."""
    return {t.lower() for t in _TAG.findall(html)} - ALLOWED_TAGS


def md_inline(text: str) -> str:
    """Render one line of Markdown without the wrapping paragraph."""
    html = md_to_html(text).strip()
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        return html[3:-4]
    return html


def code_lines(code: str, language: str) -> list[str]:
    """Highlight code and return one HTML string per source line.

    Args:
        code: Source code.
        language: A key of ``LEXERS``.

    Returns:
        Highlighted HTML for each line, without trailing newlines.
    """
    lexer = get_lexer_by_name(LEXERS[language], stripnl=False, ensurenl=True)
    # With nowrap, Pygments closes every token span at the end of each line.
    html = highlight(code.rstrip("\n") + "\n", lexer, HtmlFormatter(nowrap=True))
    lines = html.rstrip("\n").split("\n")
    expected = len(code.rstrip("\n").split("\n"))
    if len(lines) != expected:
        raise ValueError(f"highlighter returned {len(lines)} lines, expected {expected}")
    return lines


def pygments_css() -> str:
    """Stylesheet for highlighted code, light theme."""
    return str(HtmlFormatter(style="friendly").get_style_defs(f".{CSS_CLASS}, .code"))
