"""Quality gates for the search index.

- Every lesson appears once, with every recap card.
- Search text is plain: no code fences or table pipes survive. Code keeps its own `**`.
- Key terms are short bold phrases from the concept section.
"""

from __future__ import annotations

from learnkit.loader import load_course
from learnkit.search import bold_terms, build_search_index, plain_text

COURSE = load_course()
INDEX = build_search_index(COURSE)


def test_every_lesson_and_card_is_indexed() -> None:
    lessons = COURSE.lessons()
    assert [entry["id"] for entry in INDEX["lessons"]] == [lesson.id for lesson in lessons]
    assert len(INDEX["cards"]) == sum(len(lesson.recap) for lesson in lessons)
    known = {lesson.id for lesson in lessons}
    assert all(card["lesson"] in known for card in INDEX["cards"])
    assert all(term["lesson"] in known for term in INDEX["terms"])


def test_search_text_is_plain() -> None:
    for entry in INDEX["lessons"]:
        assert entry["text"], entry["id"]
        for marker in ("```", "|"):
            assert marker not in entry["text"], (entry["id"], marker)


def test_plain_text_strips_markdown() -> None:
    markdown = (
        "## Heading\n\n- **Bold** and *italic* with `code` and [a link](https://example.org).\n\n"
        "```python\nx = 1\n```"
    )
    assert plain_text(markdown) == "Heading Bold and italic with code and a link. x = 1"


def test_bold_terms_keep_short_phrases_once() -> None:
    markdown = (
        "**Data governance** decides. **Data governance** again. "
        "**no** and **a phrase far too long to be a term**."
    )
    assert bold_terms(markdown) == ["Data governance"]
