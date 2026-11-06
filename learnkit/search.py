"""The search index the app loads on its search page.

One entry per lesson (title, module and plain text), one per recap card, and one per key
term. Key terms are the phrases a concept section sets in bold, which is how lessons
mark a term they define.
"""

from __future__ import annotations

import re
from typing import Any

from learnkit.loader import Course

FENCE = re.compile(r"(?m)^\s*```[\w-]*\s*$")
BOLD = re.compile(r"\*\*(.+?)\*\*")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
CODE = re.compile(r"`([^`]*)`")
MARKERS = re.compile(r"(?m)^\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s?)")
TABLE_RULE = re.compile(r"(?m)^\s*\|?\s*:?-{3,}.*$")
EMPHASIS = re.compile(r"(?<![\w*])[*_]{1,2}(?=\S)(.+?)(?<=\S)[*_]{1,2}(?![\w*])")
SPACE = re.compile(r"\s+")
MAX_TERM_WORDS = 4
MIN_TERM_CHARS = 3


def plain_text(markdown: str) -> str:
    """Markdown reduced to the words a reader sees, on one line.

    Args:
        markdown: Lesson text in the course's Markdown subset.

    Returns:
        The text without emphasis, code ticks, link targets, list markers or table rules.
    """
    text = FENCE.sub(" ", markdown)
    text = TABLE_RULE.sub(" ", text)
    text = LINK.sub(r"\1", text)
    text = CODE.sub(r"\1", text)
    text = BOLD.sub(r"\1", text)
    text = EMPHASIS.sub(r"\1", text)
    text = MARKERS.sub("", text)
    text = text.replace("|", " ")
    return SPACE.sub(" ", text).strip()


def bold_terms(markdown: str) -> list[str]:
    """The phrases a concept section sets in bold, in order and without repeats.

    Args:
        markdown: A concept section.

    Returns:
        Each bold phrase of MIN_TERM_CHARS characters to MAX_TERM_WORDS words, as plain text.
    """
    terms: list[str] = []
    for match in BOLD.finditer(markdown):
        term = plain_text(match.group(1)).rstrip(":.,")
        short = len(term.split()) <= MAX_TERM_WORDS
        if len(term) >= MIN_TERM_CHARS and short and term not in terms:
            terms.append(term)
    return terms


def build_search_index(course: Course) -> dict[str, Any]:
    """Every lesson, recap card and key term, in syllabus order.

    Args:
        course: The loaded course.

    Returns:
        A dict with ``lessons``, ``cards`` and ``terms`` lists for site/content/search.json.
    """
    lessons: list[dict[str, str]] = []
    cards: list[dict[str, str]] = []
    terms: list[dict[str, str]] = []
    for module in course.modules.values():
        where = f"{module.meta.id} {module.meta.title}"
        for lesson in module.lessons:
            body = " ".join(
                plain_text(part)
                for part in (lesson.concept, lesson.why_it_matters, lesson.worked_example.takeaway)
            )
            lessons.append({"id": lesson.id, "title": lesson.title, "where": where, "text": body})
            cards.extend(
                {"lesson": lesson.id, "front": plain_text(c.front), "back": plain_text(c.back)}
                for c in lesson.recap
            )
            terms.extend({"lesson": lesson.id, "term": t} for t in bold_terms(lesson.concept))
    return {"lessons": lessons, "cards": cards, "terms": terms}
