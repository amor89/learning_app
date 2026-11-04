"""Cheat sheets: one page or two per module or pathway stage, built from lesson content.

A cheat sheet holds, for each lesson, its takeaway, the code snippets from its
concept section and its recap cards. It holds no text of its own, so it never
drifts from the lessons.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from learnkit.handbook import Code, code_html, prose_blocks
from learnkit.loader import Course, ModuleContent
from learnkit.models import Lesson
from learnkit.render import code_lines, md_inline

PREFIX = "cheatsheet-"


@dataclass(frozen=True)
class SheetScope:
    """One downloadable cheat sheet: a module, or a stage of a pathway."""

    stem: str
    title: str
    subtitle: str
    modules: list[ModuleContent]

    def lessons(self) -> list[Lesson]:
        """Every lesson on the sheet, in order."""
        return [lesson for module in self.modules for lesson in module.lessons]


def module_stem(module_id: str) -> str:
    """File stem of a module's cheat sheet."""
    return f"{PREFIX}{module_id}"


def stage_stem(pathway_id: str, stage_id: str) -> str:
    """File stem of a pathway stage's cheat sheet."""
    return f"{PREFIX}{pathway_id}-{stage_id}"


def sheet_scopes(course: Course) -> list[SheetScope]:
    """A sheet for every module with lessons, and for every pathway stage with lessons."""
    scopes = [
        SheetScope(module_stem(m.meta.id), f"{m.meta.id} {m.meta.title}", m.meta.summary, [m])
        for m in course.modules.values()
        if m.lessons
    ]
    for pathway in course.pathways:
        for stage in pathway.stages:
            modules = [course.modules[mid] for mid in stage.modules if course.modules[mid].lessons]
            if modules:
                stem = stage_stem(pathway.id, stage.id)
                scopes.append(SheetScope(stem, stage.title, pathway.title, modules))
    return scopes


def concept_snippets(lesson: Lesson) -> list[Code]:
    """The fenced code blocks of a lesson's concept section."""
    return [block for block in prose_blocks(lesson.concept) if isinstance(block, Code)]


def lesson_data(lesson: Lesson) -> dict[str, object]:
    """The same points as lesson_html, as data the app renders itself."""
    return {
        "id": lesson.id,
        "title": lesson.title,
        "takeaway_html": md_inline(lesson.worked_example.takeaway.strip()),
        "snippets": [code_lines(code.code, code.language) for code in concept_snippets(lesson)],
        "recap": [
            {"front_html": md_inline(card.front), "back_html": md_inline(card.back)}
            for card in lesson.recap
        ],
    }


def module_sheet_data(module: ModuleContent, pdf: str | None) -> dict[str, object]:
    """A module's cheat sheet for the app: every lesson's points and the PDF link."""
    return {
        "id": module.meta.id,
        "title": module.meta.title,
        "summary": module.meta.summary,
        "pdf": pdf,
        "lessons": [lesson_data(lesson) for lesson in module.lessons],
    }


def lesson_html(lesson: Lesson) -> str:
    """Takeaway, concept snippets and recap cards for one lesson."""
    rows = "".join(
        f"<tr><th>{md_inline(card.front)}</th><td>{md_inline(card.back)}</td></tr>"
        for card in lesson.recap
    )
    snippets = "".join(code_html(code) for code in concept_snippets(lesson))
    return (
        f'<section class="lesson" id="lesson-{lesson.id}">'
        f"<h3>{html.escape(lesson.id)} {html.escape(lesson.title)}</h3>"
        f'<p class="takeaway">{md_inline(lesson.worked_example.takeaway.strip())}</p>'
        f"{snippets}"
        f'<table class="recap"><tbody>{rows}</tbody></table>'
        "</section>"
    )


def render_sheet(scope: SheetScope, css: str) -> str:
    """One standalone HTML document for WeasyPrint."""
    parts = [
        f"<h1>{html.escape(scope.title)}</h1>",
        f'<p class="subtitle">{html.escape(scope.subtitle)}</p>',
    ]
    for module in scope.modules:
        if len(scope.modules) > 1:
            parts.append(f"<h2>{html.escape(module.meta.id)} {html.escape(module.meta.title)}</h2>")
        parts += [lesson_html(lesson) for lesson in module.lessons]
    title = f"Cheat sheet: {scope.title}"
    return (
        '<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title><style>{css}</style></head>"
        f"<body>{''.join(parts)}</body></html>"
    )
