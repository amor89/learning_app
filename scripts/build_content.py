"""Build the app's content bundle from content/*.yaml.

Writes:
    site/content/index.json          syllabus, roadmap bands and download links
    site/content/lessons/<id>.json   one rendered lesson per file
    site/content/sheets/<id>.json    one module cheat sheet per file, for the in-app view
    site/content/interview.json      timed theory questions and from-scratch tasks
    site/content/placement.json      the placement quiz for each track's start-here module
    site/content/roles.json          role plans: phases, competencies, lesson maps and gaps
    site/content/search.json         lessons, recap cards and key terms for the search page
    site/py/checkers/*.py            the checker package for Pyodide
    site/app/highlight.css           Pygments styles for light and dark themes

Run from the repository root: ``python scripts/build_content.py``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pygments.formatters import HtmlFormatter  # noqa: E402

from learnkit.brief import Brief, checker_parts, code_brief, fix_brief  # noqa: E402
from learnkit.cheatsheet import module_sheet_data, module_stem, stage_stem  # noqa: E402
from learnkit.loader import (  # noqa: E402
    Course,
    Interview,
    ModuleContent,
    load_course,
    load_interview,
    load_months,
    load_placement,
    load_roles,
)
from learnkit.models import (  # noqa: E402
    CodeExercise,
    CodeSample,
    DesignExercise,
    Exercise,
    FillGapExercise,
    InterviewTask,
    Lesson,
    McqExercise,
    PlacementQuiz,
    PredictOutputExercise,
    Role,
    SpotBugExercise,
    TheoryQuestion,
)
from learnkit.render import CSS_CLASS, code_lines, md_inline, md_to_html, unknown_tags  # noqa: E402
from learnkit.search import build_search_index  # noqa: E402

SITE = ROOT / "site"
OUT = SITE / "content"
DOWNLOADS = SITE / "downloads"
TEST_FIXTURE = ROOT / "tests" / "app" / "exercises.generated.json"
HIDDEN_KEY_MODULES = {"D7", "X3"}
XP_PER_LEVEL = 10
TASK_STEPS = [
    "Read the task and the checks below. Open the algorithm reminder only if you need it.",
    "Start the clock, then write your code in the editor.",
    "Run checks as often as you like. The clock stops when every check passes.",
]


def write_json(path: Path, data: Any) -> None:
    """Write compact, stable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8")


def render_sample(sample: CodeSample, language: str) -> dict[str, Any]:
    """Render one side of a worked example."""
    return {
        "lines": code_lines(sample.code, language),
        "notes": [{"line": n, "html": md_inline(note)} for n, note in sample.annotated_lines()],
    }


def render_brief(brief: Brief, language: str) -> dict[str, Any]:
    """Render the pre-editor brief with inline Markdown and highlighted code."""
    return {
        "steps_html": [md_inline(s) for s in brief.steps],
        "must_html": [md_inline(m) for m in brief.must],
        "checks": [
            {"message_html": md_inline(c.message), "lines": code_lines(c.code, "python")}
            for c in brief.checks
        ],
        "shape": [
            {"lines": code_lines(d.code, language), "summary_html": md_inline(d.summary)}
            for d in brief.shape
        ],
        "shape_note": brief.shape_note,
        "include_html": [md_inline(m) for m in brief.include],
        "avoid_html": [md_inline(m) for m in brief.avoid],
    }


def render_exercise(ex: Exercise, hide_key: bool) -> dict[str, Any]:
    """Serialise one exercise for the browser.

    Drops seeded bugs and code wrong answers, which only the test suite needs.
    Adds rendered HTML for prompts, hints and explanations.
    """
    data = ex.model_dump(mode="json", exclude={"seeded_bugs", "fix_seeded_bugs", "spark_tests"})
    data["prompt_html"] = md_to_html(ex.prompt)
    data["primer_html"] = md_to_html(ex.primer) if ex.primer else ""
    data["hints_html"] = [md_inline(h) for h in ex.hints]
    data["explanation_html"] = md_to_html(ex.explanation)
    data["xp"] = ex.difficulty * XP_PER_LEVEL
    if isinstance(ex, CodeExercise):
        data.pop("wrong_answers", None)
        data["solution_lines"] = code_lines(ex.solution, ex.language)
        data["brief"] = render_brief(code_brief(ex, show_shape=not hide_key), ex.language)
    if isinstance(ex, SpotBugExercise) and ex.fix_solution:
        data["fix_solution_lines"] = code_lines(ex.fix_solution, ex.language)
    if isinstance(ex, SpotBugExercise):
        brief = fix_brief(ex)
        if brief:
            data["fix_brief"] = render_brief(brief, ex.language)
    if isinstance(ex, DesignExercise):
        data["model_answer_html"] = md_to_html(ex.model_answer)
    if isinstance(ex, McqExercise):
        data["options_html"] = {o.id: md_inline(o.text) for o in ex.options}
        data["reasons_html"] = {r.id: md_inline(r.text) for r in ex.reasons}
    if isinstance(ex, PredictOutputExercise | SpotBugExercise):
        data["code_lines"] = code_lines(ex.code, ex.language)
    if isinstance(ex, FillGapExercise):
        data["template_lines"] = ex.template.rstrip("\n").split("\n")
    if hide_key:
        data = hide_answer_key(data)
    return data


def hide_answer_key(data: dict[str, Any]) -> dict[str, Any]:
    """Move answer fields into a base64 blob, so the key is not readable by accident."""
    secret_fields = {
        "answer",
        "reason_answer",
        "bug_lines",
        "solution",
        "fix_solution",
        "explanation",
        "explanation_html",
        "wrong_answers",
        "gaps",
        "accepted",
        "model_answer",
        "model_answer_html",
        "solution_lines",
        "fix_solution_lines",
    }
    secret = {k: data.pop(k) for k in list(data) if k in secret_fields}
    data["sealed"] = base64.b64encode(json.dumps(secret).encode()).decode()
    return data


def render_lesson(lesson: Lesson, module: ModuleContent) -> dict[str, Any]:
    """Render a lesson to the JSON shape the app reads."""
    example = lesson.worked_example
    hide = module.meta.id in HIDDEN_KEY_MODULES
    practical = None
    if lesson.practical:
        suffix = "ipynb" if lesson.practical.cells else "pdf"
        practical = {
            "platform": lesson.practical.platform,
            "title": lesson.practical.title,
            "intro_html": md_to_html(lesson.practical.intro),
            "download": f"downloads/practicals/{lesson.id}.{suffix}",
        }
    return {
        "id": lesson.id,
        "title": lesson.title,
        "module": module.meta.id,
        "track": module.track_id,
        "tags": module.meta.tags,
        "concept_html": md_to_html(lesson.concept),
        "why_html": md_to_html(lesson.why_it_matters),
        "example": {
            "language": example.language,
            "weak": render_sample(example.weak, example.language),
            "strong": render_sample(example.strong, example.language),
            "takeaway_html": md_to_html(example.takeaway),
        },
        "exercises": [render_exercise(ex, hide) for ex in lesson.exercises],
        "recap": [
            {"id": f"{lesson.id}#{i}", "front": md_inline(c.front), "back": md_inline(c.back)}
            for i, c in enumerate(lesson.recap)
        ],
        "claims": [c.model_dump() for c in lesson.claims],
        "practical": practical,
    }


def check_html(node: Any, where: str) -> None:
    """Fail the build when rendered content holds a tag lessons should never produce.

    Raises:
        ValueError: With the lesson field and the unexpected tags.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and (key.endswith("html") or key in {"front", "back"}):
                bad = unknown_tags(value)
                if bad:
                    raise ValueError(f"{where}.{key}: unexpected HTML tags {sorted(bad)}")
            else:
                check_html(value, f"{where}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            if isinstance(value, str):
                bad = unknown_tags(value)
                if bad and where.endswith("html"):
                    raise ValueError(f"{where}[{i}]: unexpected HTML tags {sorted(bad)}")
            else:
                check_html(value, f"{where}[{i}]")


def download_links(stem: str) -> dict[str, str] | None:
    """Return handbook links for a stem when both files exist."""
    pdf = DOWNLOADS / f"{stem}.pdf"
    docx = DOWNLOADS / f"{stem}.docx"
    if pdf.exists() and docx.exists():
        return {"pdf": f"downloads/{pdf.name}", "docx": f"downloads/{docx.name}"}
    return None


def quickref_link(stem: str) -> str | None:
    """Path of a month's quick reference when its PDF exists."""
    pdf = DOWNLOADS / "quickref" / f"{stem}.pdf"
    return f"downloads/quickref/{pdf.name}" if pdf.exists() else None


def months_index(course: Course) -> dict[str, Any]:
    """The roadmap months: their stage, modules and quick-reference PDF."""
    months = load_months(course)
    return {
        "pathway": months[0].pathway.id,
        "stages": [
            {
                "id": m.stage.id,
                "title": m.stage.title,
                "summary": m.stage.summary,
                "modules": [module.meta.id for module in m.modules],
                "quickref": quickref_link(m.stem),
            }
            for m in months
        ],
    }


def sheet_link(stem: str) -> str | None:
    """Path of a cheat sheet when its PDF exists."""
    pdf = DOWNLOADS / "cheatsheets" / f"{stem}.pdf"
    return f"downloads/cheatsheets/{pdf.name}" if pdf.exists() else None


def pathway_index(course: Course) -> list[dict[str, Any]]:
    """Pathways with a cheat-sheet link on each stage."""
    return [
        {
            "id": p.id,
            "title": p.title,
            "summary": p.summary,
            "stages": [
                {**s.model_dump(), "cheatsheet": sheet_link(stage_stem(p.id, s.id))}
                for s in p.stages
            ],
        }
        for p in course.pathways
    ]


def build_index(
    course: Course, version: str, placement: dict[str, PlacementQuiz] | None = None
) -> dict[str, Any]:
    """Syllabus index with lesson summaries, download links and placement quizzes."""
    placement = placement or {}
    tracks = []
    for track in course.tracks:
        modules = []
        for module in course.track_modules(track.id):
            modules.append(
                {
                    "id": module.meta.id,
                    "title": module.meta.title,
                    "tags": module.meta.tags,
                    "summary": module.meta.summary,
                    "downloads": download_links(f"handbook-{module.meta.id}"),
                    "cheatsheet": sheet_link(module_stem(module.meta.id)),
                    "lessons": [
                        {
                            "id": lesson.id,
                            "title": lesson.title,
                            "exercises": [e.id for e in lesson.exercises],
                            "xp": sum(e.difficulty * XP_PER_LEVEL for e in lesson.exercises),
                            "practical": lesson.practical.platform if lesson.practical else None,
                        }
                        for lesson in module.lessons
                    ],
                }
            )
        tracks.append(
            {
                "id": track.id,
                "title": track.title,
                "summary": track.summary,
                "downloads": download_links(f"handbook-{track.id}"),
                "placement": (
                    {
                        "module": placement[track.id].module,
                        "pass_mark": placement[track.id].pass_mark,
                        "count": len(placement[track.id].questions),
                    }
                    if track.id in placement
                    else None
                ),
                "modules": modules,
            }
        )
    return {
        "version": version,
        "bands": [b.model_dump() for b in course.roadmap.bands],
        "tracks": tracks,
        "pathways": pathway_index(course),
        "months": months_index(course),
        "roles": [{"id": r.id, "title": r.title, "pathway": r.pathway} for r in load_roles(course)],
        "downloads": download_links("handbook-full"),
    }


def lesson_refs(lesson_ids: list[str], titles: dict[str, str]) -> list[dict[str, str]]:
    """Lesson IDs with titles, for links back to the lessons that teach an item."""
    return [{"id": lesson_id, "title": titles[lesson_id]} for lesson_id in lesson_ids]


def render_question(question: TheoryQuestion, topic: str, titles: dict[str, str]) -> dict[str, Any]:
    """Serialise one theory question for the interview drill."""
    return {
        "id": question.id,
        "topic": topic,
        "kind": question.kind,
        "seconds": question.seconds,
        "lessons": lesson_refs(question.lessons, titles),
        "question_html": md_to_html(question.question),
        "options": [{"id": o.id, "html": md_inline(o.text)} for o in question.options],
        "answer": question.answer,
        "points_html": [md_inline(point) for point in question.points],
        "model_answer_html": md_to_html(question.model_answer),
    }


def render_task(task: InterviewTask, titles: dict[str, str]) -> dict[str, Any]:
    """Serialise one from-scratch task, with the brief the lessons' code exercises use."""
    checks, include, avoid = checker_parts(task.checker)
    brief = Brief(
        steps=TASK_STEPS,
        must=[c.message for c in checks],
        checks=checks,
        include=include,
        avoid=avoid,
    )
    return {
        "id": task.id,
        "title": task.title,
        "minutes": task.minutes,
        "lessons": lesson_refs(task.lessons, titles),
        "prompt_html": md_to_html(task.prompt),
        "primer_html": md_to_html(task.primer) if task.primer else "",
        "starter": task.starter,
        "packages": task.packages,
        "checker": task.checker.model_dump(mode="json"),
        "brief": render_brief(brief, "python"),
        "hints_html": [md_inline(h) for h in task.hints],
        "solution_lines": code_lines(task.solution, "python"),
        "explanation_html": md_to_html(task.explanation),
        "follow_ups": [
            {"question_html": md_inline(f.question), "answer_html": md_to_html(f.answer)}
            for f in task.follow_ups
        ],
    }


def build_interview(course: Course, interview: Interview) -> dict[str, Any]:
    """The interview bank as the app reads it."""
    titles = {lesson.id: lesson.title for lesson in course.lessons()}
    return {
        "topics": [
            {"id": t.id, "title": t.title, "count": len(interview.questions[t.id])}
            for t in interview.topics
        ],
        "questions": [
            render_question(q, topic.id, titles)
            for topic in interview.topics
            for q in interview.questions[topic.id]
        ],
        "tasks": [render_task(task, titles) for task in interview.tasks],
    }


def build_placement(course: Course, quizzes: list[PlacementQuiz]) -> dict[str, Any]:
    """Each track's placement quiz, with the module you skip to on a pass."""
    titles = {lesson.id: lesson.title for lesson in course.lessons()}
    tracks = {track.id: track for track in course.tracks}
    out = []
    for quiz in quizzes:
        start, after = tracks[quiz.track].modules[0], tracks[quiz.track].modules[1]
        out.append(
            {
                "track": quiz.track,
                "track_title": tracks[quiz.track].title,
                "module": {"id": start.id, "title": start.title},
                "next": {"id": after.id, "title": after.title},
                "pass_mark": quiz.pass_mark,
                "lessons": lesson_refs(
                    [lesson.id for lesson in course.modules[start.id].lessons], titles
                ),
                "questions": [
                    {
                        "id": q.id,
                        "lessons": lesson_refs(q.lessons, titles),
                        "question_html": md_to_html(q.question),
                        "options": [{"id": o.id, "html": md_inline(o.text)} for o in q.options],
                        "answer": q.answer,
                        "explanation_html": md_to_html(q.explanation),
                    }
                    for q in quiz.questions
                ],
            }
        )
    return {"quizzes": out}


def build_roles(course: Course, roles: list[Role]) -> dict[str, Any]:
    """Role plans as the app reads them, with lesson titles and modules for the links."""
    lessons = {
        lesson.id: {"id": lesson.id, "title": lesson.title, "module": module.meta.id}
        for module in course.modules.values()
        for lesson in module.lessons
    }
    return {
        "roles": [
            {
                "id": role.id,
                "title": role.title,
                "version": role.version,
                "status_html": md_inline(role.status),
                "start": role.start.isoformat(),
                "pathway": role.pathway,
                "levels": [lv.model_dump() for lv in role.levels],
                "streams": role.streams,
                "phases": [
                    {**ph.model_dump(), "success_html": md_inline(ph.success)} for ph in role.phases
                ],
                "modules": [
                    {
                        **m.model_dump(exclude={"lessons"}),
                        "lessons": [lessons[lid] for lid in m.lessons],
                        "assessment_html": md_inline(m.assessment),
                        "gaps_html": md_inline(m.gaps) if m.gaps else "",
                    }
                    for m in role.modules
                ],
                "assumptions": role.assumptions,
            }
            for role in roles
        ]
    }


def copy_checkers() -> None:
    """Copy the checker package where the Pyodide worker can fetch it."""
    target = SITE / "py" / "checkers"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for source in sorted((ROOT / "checkers").glob("*.py")):
        shutil.copy2(source, target / source.name)
    names = sorted(p.name for p in target.glob("*.py"))
    write_json(SITE / "py" / "manifest.json", {"checkers": names})


def write_highlight_css() -> None:
    """Pygments styles: light by default, dark under the dark theme."""
    light = HtmlFormatter(style="friendly").get_style_defs([f".{CSS_CLASS}", ".code"])
    dark = HtmlFormatter(style="monokai").get_style_defs(
        [f":root[data-theme='dark'] .{CSS_CLASS}", ":root[data-theme='dark'] .code"]
    )
    dark_auto = HtmlFormatter(style="monokai").get_style_defs(
        [f":root:not([data-theme='light']) .{CSS_CLASS}", ":root:not([data-theme='light']) .code"]
    )
    css = (
        "/* Generated by scripts/build_content.py. Do not edit. */\n"
        f"{light}\n{dark}\n@media (prefers-color-scheme: dark) {{\n{dark_auto}\n}}\n"
    )
    (SITE / "app" / "highlight.css").write_text(css, encoding="utf-8")


def all_exercises(course: Course) -> list[Exercise]:
    """Every exercise with its full key, for the JavaScript quality gates."""
    return [ex for lesson in course.lessons() for ex in lesson.exercises]


APP_FILES = ["site/index.html", "site/sw.js", "site/app/*.js", "site/app/styles.css"]


def content_version() -> str:
    """Hash of every content, checker, renderer and app file, so the app can spot new deploys.

    The app compares this with the version it loaded and offers a reload when they differ.
    """
    digest = hashlib.sha256()
    sources = [
        *ROOT.glob("content/**/*.yaml"),
        *ROOT.glob("checkers/*.py"),
        *ROOT.glob("learnkit/*.py"),
        *(path for pattern in APP_FILES for path in ROOT.glob(pattern)),
        Path(__file__),
    ]
    for path in sorted(sources):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def main() -> None:
    """Validate content and write the bundle."""
    course = load_course()
    lessons_dir = OUT / "lessons"
    if lessons_dir.exists():
        shutil.rmtree(lessons_dir)
    for module in course.modules.values():
        for lesson in module.lessons:
            rendered = render_lesson(lesson, module)
            check_html(rendered, lesson.id)
            write_json(lessons_dir / f"{lesson.id}.json", rendered)
    sheets_dir = OUT / "sheets"
    if sheets_dir.exists():
        shutil.rmtree(sheets_dir)
    for module in course.modules.values():
        if module.lessons:
            sheet = module_sheet_data(module, sheet_link(module_stem(module.meta.id)))
            check_html(sheet, f"sheet {module.meta.id}")
            write_json(sheets_dir / f"{module.meta.id}.json", sheet)
    interview = build_interview(course, load_interview(course))
    check_html(interview, "interview")
    write_json(OUT / "interview.json", interview)
    roles = build_roles(course, load_roles(course))
    check_html(roles, "roles")
    write_json(OUT / "roles.json", roles)
    quizzes = load_placement(course)
    placement = build_placement(course, quizzes)
    check_html(placement, "placement")
    write_json(OUT / "placement.json", placement)
    write_json(OUT / "search.json", build_search_index(course))
    version = content_version()
    write_json(OUT / "index.json", build_index(course, version, {q.track: q for q in quizzes}))
    write_json(TEST_FIXTURE, [ex.model_dump(mode="json") for ex in all_exercises(course)])
    copy_checkers()
    write_highlight_css()
    print(
        f"Built {len(course.lessons())} lessons, {len(interview['questions'])} interview "
        f"questions and {len(interview['tasks'])} tasks, version {version}"
    )


if __name__ == "__main__":
    main()
