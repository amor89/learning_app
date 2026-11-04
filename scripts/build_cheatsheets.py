"""Build cheat sheets: one A5 PDF per module and per pathway stage.

Each sheet lists, for every lesson, its takeaway, its concept code snippets and
its recap cards. Output goes to site/downloads/cheatsheets/ and is committed,
so GitHub Pages serves it.

Run from the repository root: ``python scripts/build_cheatsheets.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pygments.formatters import HtmlFormatter  # noqa: E402
from weasyprint import HTML  # noqa: E402

from learnkit.cheatsheet import render_sheet, sheet_scopes  # noqa: E402
from learnkit.loader import load_course  # noqa: E402
from learnkit.render import CSS_CLASS  # noqa: E402

OUT = ROOT / "site" / "downloads" / "cheatsheets"

SHEET_CSS = """
@page {
  size: A5;
  margin: 10mm 8mm 11mm 8mm;
  @top-right { content: string(sheet); font: 6.5pt "DejaVu Sans"; color: #5b6875; }
  @bottom-center {
    content: counter(page) " / " counter(pages); font: 6.5pt "DejaVu Sans"; color: #5b6875;
  }
}
html { font: 8pt/1.35 "DejaVu Sans", "Liberation Sans", sans-serif; color: #17212b; }
h1 { font-size: 13pt; color: #1f5f8b; margin: 0; string-set: sheet content(); }
.subtitle { color: #5b6875; margin: 1pt 0 6pt; font-size: 7.5pt; }
h2 {
  font-size: 10pt; color: #fff; background: #1f5f8b; padding: 2pt 4pt; margin: 8pt 0 3pt;
  break-after: avoid;
}
h3 {
  font-size: 8.6pt; margin: 6pt 0 2pt; color: #1f5f8b; border-bottom: 0.5pt solid #d5dbe3;
  break-after: avoid;
}
section.lesson { break-inside: auto; }
p { margin: 2pt 0; }
.takeaway { font-style: italic; }
code { font: 7pt "DejaVu Sans Mono", monospace; background: #eef1f5; padding: 0 1pt; }
table { border-collapse: collapse; width: 100%; margin: 2pt 0; }
table.recap th, table.recap td {
  border: 0.4pt solid #d5dbe3; padding: 1.5pt 3pt; font-size: 7.4pt;
  vertical-align: top; text-align: left;
}
table.recap th { width: 32%; background: #eef1f5; font-weight: bold; }
table.recap tr, table.codetable tr { break-inside: avoid; }
table.codetable {
  background: #f5f7fa; border: 0.4pt solid #d5dbe3; table-layout: fixed;
  font: 6.6pt/1.3 "DejaVu Sans Mono", monospace;
}
table.codetable td { border: 0; padding: 0 2pt; font-size: 6.6pt; }
table.codetable td.lnum { width: 12pt; text-align: right; color: #8a96a3; }
table.codetable td.src {
  white-space: pre-wrap; overflow-wrap: break-word; padding-left: 12pt; text-indent: -9pt;
}
"""


def main() -> None:
    """Build every cheat sheet and remove stale ones."""
    course = load_course()
    OUT.mkdir(parents=True, exist_ok=True)
    css = SHEET_CSS + str(HtmlFormatter(style="friendly").get_style_defs(f".{CSS_CLASS}"))
    keep = []
    for scope in sheet_scopes(course):
        path = OUT / f"{scope.stem}.pdf"
        HTML(string=render_sheet(scope, css), base_url=str(ROOT)).write_pdf(str(path))
        keep.append(path.name)
    for stale in OUT.glob("cheatsheet-*.pdf"):
        if stale.name not in keep:
            stale.unlink()
    (OUT / "manifest.json").write_text(json.dumps(sorted(keep), indent=1) + "\n", encoding="utf-8")
    print(f"Built {len(keep)} cheat sheets in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
