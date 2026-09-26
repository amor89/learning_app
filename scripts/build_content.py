"""Build the app's content bundle from content/*.yaml.

Writes:
    site/content/index.json          syllabus, roadmap bands and download links
    site/content/lessons/<id>.json   one rendered lesson per file
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

from learnkit.loader import Course, ModuleContent, load_course  # noqa: E402
from learnkit.models import (  # noqa: E402
    CodeExercise,
    CodeSample,
    DesignExercise,
    Exercise,
    FillGapExercise,
    Lesson,
    McqExercise,
    PredictOutputExercise,
    SpotBugExercise,
)
from learnkit.render import CSS_CLASS, code_lines, md_inline, md_to_html, unknown_tags  # noqa: E402

SITE = ROOT / "site"
OUT = SITE / "content"
DOWNLOADS = SITE / "downloads"
TEST_FIXTURE = ROOT / "tests" / "app" / "exercises.generated.json"
HIDDEN_KEY_MODULES = {"D7", "X3"}
XP_PER_LEVEL = 10


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


def render_exercise(ex: Exercise, hide_key: bool) -> dict[str, Any]:
    """Serialise one exercise for the browser.

    Drops seeded bugs and code wrong answers, which only the test suite needs.
    Adds rendered HTML for prompts, hints and explanations.
    """
    data = ex.model_dump(mode="json", exclude={"seeded_bugs", "fix_seeded_bugs", "spark_tests"})
    data["prompt_html"] = md_to_html(ex.prompt)
    data["hints_html"] = [md_inline(h) for h in ex.hints]
    data["explanation_html"] = md_to_html(ex.explanation)
    data["xp"] = ex.difficulty * XP_PER_LEVEL
    if isinstance(ex, CodeExercise):
        data.pop("wrong_answers", None)
        data["solution_lines"] = code_lines(ex.solution, ex.language)
    if isinstance(ex, SpotBugExercise) and ex.fix_solution:
        data["fix_solution_lines"] = code_lines(ex.fix_solution, ex.language)
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


def build_index(course: Course, version: str) -> dict[str, Any]:
    """Syllabus index with lesson summaries and download links."""
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
                    "lessons": [
                        {
                            "id": lesson.id,
                            "title": lesson.title,
                            "exercises": [e.id for e in lesson.exercises],
                            "xp": sum(e.difficulty * XP_PER_LEVEL for e in lesson.exercises),
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
                "modules": modules,
            }
        )
    return {
        "version": version,
        "bands": [b.model_dump() for b in course.roadmap.bands],
        "tracks": tracks,
        "downloads": download_links("handbook-full"),
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
    light = HtmlFormatter(style="friendly").get_style_defs(f".{CSS_CLASS}, .code")
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


def content_version() -> str:
    """Hash of every content and checker file, so the app can spot new builds."""
    digest = hashlib.sha256()
    for path in sorted([*ROOT.glob("content/**/*.yaml"), *ROOT.glob("checkers/*.py")]):
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
    version = content_version()
    write_json(OUT / "index.json", build_index(course, version))
    write_json(TEST_FIXTURE, [ex.model_dump(mode="json") for ex in all_exercises(course)])
    copy_checkers()
    write_highlight_css()
    print(f"Built {len(course.lessons())} lessons, version {version}")


if __name__ == "__main__":
    main()
