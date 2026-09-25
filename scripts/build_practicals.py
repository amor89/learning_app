"""Export each lesson practical.

- Practicals with cells become Jupyter notebooks (.ipynb). Import them into
  Databricks Free Edition or a Fabric workspace.
- Practicals with steps only become an A5 PDF lab sheet.

Output: site/downloads/practicals/<lesson id>.ipynb or .pdf
Run from the repository root: ``python scripts/build_practicals.py``.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import nbformat  # noqa: E402
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook  # noqa: E402
from weasyprint import HTML  # noqa: E402

from learnkit.handbook import PLATFORM_LABELS  # noqa: E402
from learnkit.loader import load_course  # noqa: E402
from learnkit.models import Lesson, Practical  # noqa: E402
from learnkit.render import md_inline, md_to_html  # noqa: E402

OUT = ROOT / "site" / "downloads" / "practicals"
LAB_CSS = """
@page {
  size: A5;
  margin: 13mm 11mm;
  @bottom-center { content: counter(page); font: 7.5pt sans-serif; }
}
html { font: 9.5pt/1.5 "DejaVu Sans", sans-serif; color: #17212b; }
h1 { font-size: 14pt; color: #1f5f8b; }
code { font: 8pt "DejaVu Sans Mono", monospace; background: #eef1f5; overflow-wrap: anywhere; }
ol li { margin: 5pt 0; }
.box { border: 0.5pt solid #d5dbe3; padding: 6pt; margin-top: 10pt; }
"""


def notebook(lesson: Lesson, practical: Practical) -> nbformat.NotebookNode:
    """Build a notebook with a title cell and the practical's cells."""
    header = (
        f"# {lesson.id} practical: {practical.title}\n\n"
        f"Platform: {PLATFORM_LABELS[practical.platform]}.\n\n{practical.intro}"
    )
    cells = [new_markdown_cell(header)]
    for cell in practical.cells:
        source = cell.source.rstrip("\n")
        cells.append(new_code_cell(source) if cell.kind == "code" else new_markdown_cell(source))
    nb = new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python",
    }
    nb.metadata["language_info"] = {"name": "python"}
    return cast(nbformat.NotebookNode, nb)


def lab_pdf(lesson: Lesson, practical: Practical, path: Path) -> None:
    """Write a step-by-step lab sheet."""
    steps = "".join(f"<li>{md_inline(step)}</li>" for step in practical.steps)
    page = (
        f"<!doctype html><html lang='en-GB'><head><meta charset='utf-8'>"
        f"<style>{LAB_CSS}</style></head><body>"
        f"<h1>{html.escape(lesson.id)} lab: {html.escape(practical.title)}</h1>"
        f"<p><strong>Platform:</strong> {PLATFORM_LABELS[practical.platform]}</p>"
        f"{md_to_html(practical.intro)}<ol>{steps}</ol>"
        f"<div class='box'><strong>Notes</strong><br><br><br><br><br></div>"
        f"</body></html>"
    )
    HTML(string=page).write_pdf(str(path))


def main() -> None:
    """Export every practical and remove stale files."""
    OUT.mkdir(parents=True, exist_ok=True)
    written: set[str] = set()
    for lesson in load_course().lessons():
        practical = lesson.practical
        if practical is None:
            continue
        if practical.cells:
            path = OUT / f"{lesson.id}.ipynb"
            nb = notebook(lesson, practical)
            nbformat.validate(nb)
            nbformat.write(nb, str(path))
        else:
            path = OUT / f"{lesson.id}.pdf"
            lab_pdf(lesson, practical, path)
        written.add(path.name)
        print(f"Wrote {path.relative_to(ROOT)}")
    for stale in OUT.iterdir():
        if stale.name not in written:
            stale.unlink()


if __name__ == "__main__":
    main()
