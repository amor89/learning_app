"""Build the handbook as a neutral list of blocks from the same content the app uses.

Two renderers consume the blocks: ``render_html`` (for WeasyPrint PDF) and
``learnkit.docx_writer`` (for Word). Neither holds any lesson text of its own.
"""

from __future__ import annotations

import html
import random
import re
from dataclasses import dataclass, field
from typing import Literal

from learnkit.brief import Definition, code_brief
from learnkit.loader import Course, ModuleContent
from learnkit.models import (
    CodeExercise,
    DesignExercise,
    Exercise,
    FillGapExercise,
    Lesson,
    McqExercise,
    OrderExercise,
    PredictOutputExercise,
    SpotBugExercise,
    Track,
)
from learnkit.render import LEXERS, code_lines, md_inline, md_to_html

TYPE_LABELS = {
    "mcq": "Multiple choice",
    "fill_gap": "Fill the gap",
    "predict_output": "Predict the output",
    "order": "Put in order",
    "spot_bug": "Spot the bug",
    "write_function": "Write the function",
    "refactor": "Refactor",
    "design": "Architecture design",
}
PLATFORM_LABELS = {
    "databricks": "Databricks Free Edition",
    "fabric": "Fabric trial workspace",
    "laptop": "Laptop",
}


@dataclass
class Heading:
    level: int
    text: str
    anchor: str = ""
    kind: Literal["heading"] = "heading"


@dataclass
class Markdown:
    text: str
    kind: Literal["markdown"] = "markdown"


@dataclass
class Code:
    code: str
    language: str
    notes: list[tuple[int, str]] = field(default_factory=list)
    kind: Literal["code"] = "code"


@dataclass
class Items:
    items: list[str]
    ordered: bool = False
    checklist: bool = False
    kind: Literal["items"] = "items"


@dataclass
class PageBreak:
    kind: Literal["pagebreak"] = "pagebreak"


@dataclass
class Contents:
    entries: list[tuple[int, str, str]]
    kind: Literal["contents"] = "contents"


Block = Heading | Markdown | Code | Items | PageBreak | Contents


@dataclass
class Scope:
    """One downloadable handbook: the full course, a track or a module."""

    stem: str
    title: str
    parts: list[tuple[Track, list[ModuleContent]]]

    def lessons(self) -> list[Lesson]:
        return [lesson for _, modules in self.parts for m in modules for lesson in m.lessons]


def scopes(course: Course) -> list[Scope]:
    """Every handbook to build. Tracks and modules without lessons are skipped."""
    result: list[Scope] = []
    full_parts = []
    for track in course.tracks:
        modules = [m for m in course.track_modules(track.id) if m.lessons]
        if not modules:
            continue
        full_parts.append((track, modules))
        result.append(
            Scope(f"handbook-{track.id}", f"Track {track.id}: {track.title}", [(track, modules)])
        )
        for module in modules:
            title = f"{module.meta.id} {module.meta.title}"
            result.append(Scope(f"handbook-{module.meta.id}", title, [(track, [module])]))
    result.insert(0, Scope("handbook-full", "Full handbook", full_parts))
    return result


_FENCE = re.compile(r"^```(\w*)\n(.*?)^```\s*$", re.DOTALL | re.MULTILINE)


def prose_blocks(text: str) -> list[Block]:
    """Split Markdown into prose and code blocks.

    Fenced code becomes a Code block, so the handbook numbers its lines and wraps
    long lines with a hanging indent, like the worked examples.
    """
    blocks: list[Block] = []
    pos = 0
    for match in _FENCE.finditer(text):
        before = text[pos : match.start()].strip()
        if before:
            blocks.append(Markdown(before))
        language = match.group(1) if match.group(1) in LEXERS else "text"
        blocks.append(Code(match.group(2).rstrip("\n"), language))
        pos = match.end()
    rest = text[pos:].strip()
    if rest:
        blocks.append(Markdown(rest))
    return blocks


def lesson_anchor(lesson_id: str) -> str:
    return f"lesson-{lesson_id}"


def shuffled_items(ex: OrderExercise) -> list[str]:
    """Deterministic order for the printed puzzle, never equal to the answer."""
    ids = [item.id for item in ex.items]
    random.Random(ex.id).shuffle(ids)
    if ids == ex.answer:
        ids.reverse()
    text = {item.id: item.text for item in ex.items}
    return [text[i] for i in ids]


def shape_text(shape: list[Definition]) -> str:
    """Print the answer's definitions as stubs, each under its docstring line."""
    return "\n\n".join((f"# {d.summary}\n" if d.summary else "") + d.code for d in shape)


def exercise_blocks(ex: Exercise, number: int) -> list[Block]:
    """The exercise as a learner sees it, without answers."""
    blocks: list[Block] = [
        Heading(5, f"Exercise {number}. {TYPE_LABELS[ex.type]} (level {ex.difficulty})", ex.id),
        Markdown(ex.prompt),
    ]
    if ex.primer:
        blocks += [Markdown("**What you need to know.**"), *prose_blocks(ex.primer)]
    if isinstance(ex, McqExercise):
        blocks.append(Items([f"{o.id}) {o.text}" for o in ex.options]))
        if ex.reasons:
            blocks.append(Markdown("**Why?**"))
            blocks.append(Items([f"{r.id}) {r.text}" for r in ex.reasons]))
    elif isinstance(ex, FillGapExercise):
        gap_ids = list(ex.gaps)
        template = ex.template
        for i, gap in enumerate(gap_ids, start=1):
            template = template.replace(f"[[{gap}]]", f"_____({i})")
        blocks.append(Code(template, ex.language))
    elif isinstance(ex, PredictOutputExercise):
        blocks.append(Code(ex.code, ex.language))
    elif isinstance(ex, OrderExercise):
        blocks.append(Items(shuffled_items(ex)))
    elif isinstance(ex, SpotBugExercise):
        blocks.append(Code(ex.code, ex.language))
        tail = " Then write the fix." if ex.fix_checker else ""
        blocks.append(Markdown(f"*Write down the line number of the bug.{tail}*"))
    elif isinstance(ex, CodeExercise):
        brief = code_brief(ex)
        if brief.must:
            blocks.append(Markdown("Your code must pass these checks:"))
            blocks.append(Items(brief.must))
        if brief.shape:
            blocks.append(Markdown(f"Shape of the answer. {brief.shape_note}"))
            blocks.append(Code(shape_text(brief.shape), ex.language))
        if ex.starter:
            blocks.append(Markdown("Starter code:"))
            blocks.append(Code(ex.starter, ex.language))
    elif isinstance(ex, DesignExercise):
        options = ", ".join(o.text for o in ex.slots[0].options)
        blocks.append(Markdown(f"Options: {options}."))
        blocks.append(Items([slot.label for slot in ex.slots], ordered=True))
    return blocks


def solution_blocks(ex: Exercise, lesson: Lesson, number: int) -> list[Block]:
    """Hints, answer, explanation and common wrong answers for the appendix."""
    blocks: list[Block] = [Heading(5, f"{lesson.id} exercise {number}", f"sol-{ex.id}")]
    blocks.append(
        Markdown("**Hints.** " + " ".join(f"({i}) {h}" for i, h in enumerate(ex.hints, 1)))
    )
    if isinstance(ex, McqExercise):
        option = next(o.text for o in ex.options if o.id == ex.answer)
        answer = f"**Answer.** {ex.answer}) {option}"
        if ex.reason_answer:
            reason = next(r.text for r in ex.reasons if r.id == ex.reason_answer)
            answer += f" Because: {ex.reason_answer}) {reason}"
        blocks.append(Markdown(answer))
    elif isinstance(ex, FillGapExercise):
        filled = ex.template
        for gap, spec in ex.gaps.items():
            filled = filled.replace(f"[[{gap}]]", spec.accepted[0])
        blocks += [Markdown("**Answer.**"), Code(filled, ex.language)]
    elif isinstance(ex, PredictOutputExercise):
        blocks += [Markdown("**Answer.**"), Code(ex.answer, "text")]
    elif isinstance(ex, OrderExercise):
        text = {item.id: item.text for item in ex.items}
        blocks += [Markdown("**Answer.**"), Items([text[i] for i in ex.answer], ordered=True)]
    elif isinstance(ex, SpotBugExercise):
        lines = ", ".join(str(n) for n in ex.bug_lines)
        blocks.append(Markdown(f"**Answer.** The bug is on line {lines}."))
        if ex.fix_solution:
            blocks += [Markdown("Fixed version:"), Code(ex.fix_solution, ex.language)]
    elif isinstance(ex, CodeExercise):
        blocks += [Markdown("**Answer.**"), Code(ex.solution, ex.language)]
    elif isinstance(ex, DesignExercise):
        blocks += [Markdown("**Answer.**"), Markdown(ex.model_answer)]
    blocks += prose_blocks(ex.explanation)
    wrong = wrong_answer_notes(ex)
    if wrong:
        blocks += [Markdown("**Common wrong answers.**"), Items(wrong)]
    return blocks


def wrong_answer_notes(ex: Exercise) -> list[str]:
    """One line per listed wrong answer with its feedback."""
    if isinstance(ex, McqExercise | PredictOutputExercise):
        return [f"`{w.answer}`: {w.feedback}" for w in ex.wrong_answers]
    if isinstance(ex, FillGapExercise | DesignExercise):
        return [
            "; ".join(f"{k} = `{v}`" for k, v in w.answer.items()) + f": {w.feedback}"
            for w in ex.wrong_answers
        ]
    if isinstance(ex, SpotBugExercise):
        return [f"Line {', '.join(map(str, w.lines))}: {w.feedback}" for w in ex.wrong_answers]
    if isinstance(ex, OrderExercise):
        return [w.feedback for w in ex.wrong_answers]
    return []


def lesson_blocks(lesson: Lesson) -> list[Block]:
    """Concept, why it matters, worked example, recap card and exercises."""
    example = lesson.worked_example
    blocks: list[Block] = [
        Heading(3, f"{lesson.id} {lesson.title}", lesson_anchor(lesson.id)),
        Heading(4, "Concept"),
        *prose_blocks(lesson.concept),
        Heading(4, "Why it matters"),
        *prose_blocks(lesson.why_it_matters),
        Heading(4, "Worked example: weak code"),
        Code(example.weak.code, example.language, example.weak.annotated_lines()),
        Heading(4, "Worked example: strong code"),
        Code(example.strong.code, example.language, example.strong.annotated_lines()),
        Markdown(example.takeaway),
        Heading(4, "Recap card"),
        Items([f"**{c.front}** {c.back}" for c in lesson.recap]),
        Heading(4, "Practice"),
    ]
    for number, ex in enumerate(lesson.exercises, start=1):
        blocks += exercise_blocks(ex, number)
    if lesson.practical:
        p = lesson.practical
        blocks += [
            Heading(4, f"Practical: {p.title}"),
            Markdown(f"Platform: {PLATFORM_LABELS[p.platform]}. " + p.intro),
        ]
        if p.steps:
            blocks.append(Items(p.steps, ordered=True))
        else:
            blocks.append(Markdown(f"Download the notebook `{lesson.id}.ipynb` from the app."))
    if lesson.claims:
        blocks.append(Heading(4, "Sources"))
        blocks.append(Items([f"{c.claim} ({c.status}: {c.source})" for c in lesson.claims]))
    return blocks


def build_blocks(scope: Scope, course: Course) -> list[Block]:
    """The whole handbook for one scope."""
    labels = {b.id: b.label for b in course.roadmap.bands}
    body: list[Block] = []
    contents: list[tuple[int, str, str]] = []
    for track, modules in scope.parts:
        anchor = f"track-{track.id}"
        contents.append((1, f"Track {track.id}: {track.title}", anchor))
        body += [
            PageBreak(),
            Heading(1, f"Track {track.id}: {track.title}", anchor),
            Markdown(track.summary),
        ]
        for module in modules:
            m_anchor = f"module-{module.meta.id}"
            contents.append((2, f"{module.meta.id} {module.meta.title}", m_anchor))
            tags = "; ".join(labels[t] for t in module.meta.tags)
            body += [
                PageBreak(),
                Heading(2, f"{module.meta.id} {module.meta.title}", m_anchor),
                Markdown(f"*Roadmap: {tags}.* {module.meta.summary}"),
            ]
            for lesson in module.lessons:
                contents.append((3, f"{lesson.id} {lesson.title}", lesson_anchor(lesson.id)))
                body += lesson_blocks(lesson)
        c_anchor = f"checklist-{track.id}"
        contents.append((2, f"Track {track.id} best-practice checklist", c_anchor))
        body += [
            PageBreak(),
            Heading(2, f"Track {track.id} best-practice checklist", c_anchor),
            Items([f"☐ {item}" for item in track.checklist], checklist=True),
        ]
    contents.append((1, "Appendix: solutions and answer keys", "appendix"))
    body += [
        PageBreak(),
        Heading(1, "Appendix: solutions and answer keys", "appendix"),
        Markdown(
            "Attempt each exercise before you read its solution. Track D answer keys are here too."
        ),
    ]
    for lesson in scope.lessons():
        body.append(Heading(3, f"{lesson.id} {lesson.title}", f"sol-{lesson.id}"))
        for number, ex in enumerate(lesson.exercises, start=1):
            body += solution_blocks(ex, lesson, number)
    intro: list[Block] = [
        Heading(1, scope.title, "top"),
        Markdown(
            "Generated from the same content files as the app. "
            "Each module lists its roadmap months. Solutions are in the appendix."
        ),
        Heading(2, "Contents", "contents"),
        Contents(contents),
    ]
    return intro + body


# HTML renderer (for WeasyPrint) ------------------------------------------------


def code_html(block: Code) -> str:
    """Numbered code table. Annotated lines carry a marker; notes follow the table."""
    marks = {line: i for i, (line, _) in enumerate(block.notes, start=1)}
    rows = []
    for n, line in enumerate(code_lines(block.code, block.language), start=1):
        gutter = f'<span class="mark">{marks[n]}</span>' if n in marks else str(n)
        cls = ' class="ann"' if n in marks else ""
        rows.append(
            f'<tr{cls}><td class="lnum">{gutter}</td><td class="src">{line or " "}</td></tr>'
        )
    table = f'<table class="codetable hl"><tbody>{"".join(rows)}</tbody></table>'
    if not block.notes:
        return table
    notes = "".join(
        f'<li><span class="note-line">Line {line}.</span> {md_inline(note)}</li>'
        for line, note in block.notes
    )
    return f'{table}<ol class="notes">{notes}</ol>'


def render_html(blocks: list[Block], title: str, css: str) -> str:
    """Render blocks to one standalone HTML document."""
    parts = []
    for block in blocks:
        if isinstance(block, Heading):
            level = min(block.level, 6)
            anchor = f' id="{block.anchor}"' if block.anchor else ""
            parts.append(f"<h{level}{anchor}>{html.escape(block.text)}</h{level}>")
        elif isinstance(block, Markdown):
            parts.append(md_to_html(block.text))
        elif isinstance(block, Code):
            parts.append(code_html(block))
        elif isinstance(block, Items):
            tag = "ol" if block.ordered else "ul"
            list_class = "checklist" if block.checklist else "items"
            items = "".join(f"<li>{md_inline(item)}</li>" for item in block.items)
            parts.append(f'<{tag} class="{list_class}">{items}</{tag}>')
        elif isinstance(block, PageBreak):
            parts.append('<div class="pagebreak"></div>')
        elif isinstance(block, Contents):
            entries = "".join(
                f'<li class="toc{level}"><a href="#{anchor}">{html.escape(text)}</a></li>'
                for level, text, anchor in block.entries
            )
            parts.append(f'<ul class="toc">{entries}</ul>')
    body = "\n".join(parts)
    return (
        f'<!doctype html><html lang="en-GB"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title><style>{css}</style></head><body>{body}</body></html>"
    )
