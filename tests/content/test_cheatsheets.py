"""Cheat sheets cover every published module and stage, with every lesson's key points."""

import re

from learnkit.cheatsheet import (
    concept_snippets,
    module_stem,
    render_sheet,
    sheet_scopes,
    stage_stem,
)
from learnkit.loader import load_course
from learnkit.render import md_inline


def test_a_sheet_for_every_module_and_stage() -> None:
    course = load_course()
    stems = [s.stem for s in sheet_scopes(course)]
    assert len(stems) == len(set(stems))
    for module in course.modules.values():
        assert (module_stem(module.meta.id) in stems) == bool(module.lessons)
    for pathway in course.pathways:
        for stage in pathway.stages:
            published = any(course.modules[m].lessons for m in stage.modules)
            assert (stage_stem(pathway.id, stage.id) in stems) == published


def test_sheet_holds_takeaways_snippets_and_recap_cards() -> None:
    course = load_course()
    scope = next(s for s in sheet_scopes(course) if s.stem == stage_stem("ds-roadmap", "m1-3"))
    page = render_sheet(scope, css="")
    for lesson in scope.lessons():
        section = page.split(f'id="lesson-{lesson.id}"', 1)[1].split("</section>", 1)[0]
        assert md_inline(lesson.worked_example.takeaway.strip()) in section
        assert section.count("<tr><th>") == len(lesson.recap)
        assert section.count('class="codetable') == len(concept_snippets(lesson))
    assert "<h2>B23 PyTorch foundations</h2>" in page and "<h2>B16 " in page


def test_module_sheet_has_no_module_headings() -> None:
    course = load_course()
    scope = next(s for s in sheet_scopes(course) if s.stem == module_stem("B23"))
    assert "<h2>" not in render_sheet(scope, css="")


def test_takeaways_and_recap_cards_render_without_stray_emphasis() -> None:
    """Names such as __init__ or test_*.py need backticks, or Markdown makes them bold or italic."""
    course = load_course()
    stray = []
    for lesson in course.lessons():
        texts = [lesson.worked_example.takeaway] + [
            s for card in lesson.recap for s in (card.front, card.back)
        ]
        for text in texts:
            if "**" not in text and re.search(r"<(em|strong)>", md_inline(text)):
                stray.append((lesson.id, text))
    assert not stray, stray
