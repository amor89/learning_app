"""Quick references: one printed page per roadmap month, built from lesson content.

A quick reference holds, for each lesson of the month's modules, its takeaway and
its recap cards, with no code. It holds no text of its own, so it never drifts
from the lessons. The build fails when a month no longer fits on one page.
"""

from __future__ import annotations

import html

from learnkit.loader import MonthStage
from learnkit.models import Lesson
from learnkit.render import md_inline

QUICKREF_CSS = """
@page {
  size: A4;
  margin: 9mm 9mm 10mm 9mm;
  @bottom-right { content: string(title); font: 6pt "DejaVu Sans"; color: #5b6875; }
}
html { font: 6.9pt/1.28 "DejaVu Sans", "Liberation Sans", sans-serif; color: #17212b; }
h1 { font-size: 12pt; color: #1f5f8b; margin: 0; string-set: title content(); }
.subtitle { color: #5b6875; margin: 1pt 0 5pt; font-size: 7pt; }
.columns { column-count: 2; column-gap: 6mm; }
h2 {
  font-size: 8pt; color: #fff; background: #1f5f8b; padding: 1pt 3pt; margin: 4pt 0 2pt;
  break-after: avoid;
}
section.lesson { break-inside: avoid; margin-bottom: 3pt; }
h3 { font-size: 7.2pt; margin: 3pt 0 1pt; color: #1f5f8b; break-after: avoid; }
p { margin: 0 0 1pt; }
.takeaway { font-style: italic; }
ul { margin: 0; padding-left: 8pt; }
li { margin: 0 0 0.5pt; }
li b { color: #17212b; }
code { font: 6.3pt "DejaVu Sans Mono", monospace; background: #eef1f5; padding: 0 0.6pt; }
"""


def lesson_block(lesson: Lesson) -> str:
    """Takeaway and recap facts for one lesson, without code."""
    facts = "".join(
        f"<li><b>{md_inline(card.front)}</b>: {md_inline(card.back)}</li>" for card in lesson.recap
    )
    return (
        '<section class="lesson">'
        f"<h3>{html.escape(lesson.id)} {html.escape(lesson.title)}</h3>"
        f'<p class="takeaway">{md_inline(lesson.worked_example.takeaway.strip())}</p>'
        f"<ul>{facts}</ul>"
        "</section>"
    )


def render_quickref(month: MonthStage, css: str = QUICKREF_CSS) -> str:
    """One standalone HTML document for WeasyPrint."""
    parts = []
    for module in month.modules:
        parts.append(f"<h2>{html.escape(module.meta.id)} {html.escape(module.meta.title)}</h2>")
        parts += [lesson_block(lesson) for lesson in module.lessons]
    title = f"Quick reference: {month.stage.title}"
    return (
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title><style>{css}</style></head><body>"
        f"<h1>{html.escape(month.stage.title)}</h1>"
        f'<p class="subtitle">Quick reference · {html.escape(month.pathway.title)} · '
        f"{html.escape(month.stage.summary)}</p>"
        f'<div class="columns">{"".join(parts)}</div></body></html>'
    )
