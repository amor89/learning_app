"""Quality gates for the roadmap months and their one-page quick references.

- content/months.yaml names stages of an existing pathway, each with lessons.
- Every month's quick reference fits on one page, and lists every lesson.
"""

from __future__ import annotations

import pytest
from weasyprint import HTML

from learnkit.loader import MonthStage, load_course, load_months
from learnkit.quickref import render_quickref

COURSE = load_course()
MONTHS = load_months(COURSE)


def test_months_are_stages_of_their_pathway() -> None:
    assert MONTHS
    pathway = MONTHS[0].pathway
    stage_ids = [s.id for s in pathway.stages]
    assert all(m.pathway is pathway for m in MONTHS)
    assert [m.stage.id for m in MONTHS] == sorted(
        (m.stage.id for m in MONTHS), key=stage_ids.index
    ), "months follow the pathway's stage order"


@pytest.mark.parametrize("month", MONTHS, ids=lambda m: m.stage.id)
def test_quickref_fits_one_page(month: MonthStage) -> None:
    pages = HTML(string=render_quickref(month)).render().pages
    assert len(pages) == 1, f"{month.stem}: {len(pages)} pages"


@pytest.mark.parametrize("month", MONTHS, ids=lambda m: m.stage.id)
def test_quickref_lists_every_lesson(month: MonthStage) -> None:
    html = render_quickref(month)
    for module in month.modules:
        for lesson in module.lessons:
            assert f">{lesson.id} " in html, lesson.id
