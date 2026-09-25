"""Rendering rules shared by the app bundle and the handbook."""

from __future__ import annotations

from learnkit.render import code_lines, md_inline, md_to_html, unknown_tags


def test_raw_html_is_escaped() -> None:
    """Regression: <email> in lesson text must show as text, not become a tag."""
    html = md_inline("Clone under /Workspace/Users/<email>/ and use [dev <user>].")
    assert "&lt;email&gt;" in html and "&lt;user&gt;" in html
    assert unknown_tags(html) == set()


def test_markdown_features_still_render() -> None:
    source = "**bold** `code`\n\n- item\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```sql\nSELECT 1\n```"
    html = md_to_html(source)
    assert "<strong>bold</strong>" in html and "<table>" in html and 'class="hl"' in html
    assert unknown_tags(html) == set()


def test_code_lines_keep_line_count() -> None:
    code = 'x = """a\nb"""\n\ny = 1'
    assert len(code_lines(code, "python")) == 4


def test_handbook_html_keeps_stylesheet() -> None:
    """Regression: a local variable once shadowed the css parameter of render_html."""
    from learnkit.handbook import Items, Markdown, render_html

    blocks = [Markdown("text"), Items(["a"], checklist=True), Items(["b"])]
    page = render_html(blocks, "t", "@page { size: A5; }")
    assert "<style>@page { size: A5; }</style>" in page
    assert 'class="checklist"' in page and 'class="items"' in page
