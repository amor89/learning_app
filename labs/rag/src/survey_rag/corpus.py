"""Load the methodology notes and cut them into chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from survey_rag.steps import chunk_words

SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Chunk:
    """One retrievable passage. Grain: one window of one section of one note.

    chunk_id is "doc#section#n" and section_id is "doc#section", so a citation
    names the window and an evaluation can score at section level.
    """

    chunk_id: str
    section_id: str
    doc_id: str
    heading: str
    text: str


def slugify(heading: str) -> str:
    """Lower-case a heading and join its words with hyphens."""
    return SLUG.sub("-", heading.lower()).strip("-")


def split_sections(markdown: str) -> list[tuple[str, str]]:
    """Split a note into (heading, body) pairs at each "## " heading.

    Args:
        markdown: The note text.

    Returns:
        One pair per second-level heading, in order. Text before the first
        "## " heading is dropped.
    """
    sections: list[tuple[str, str]] = []
    heading: str | None = None
    lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            if heading is not None:
                sections.append((heading, " ".join(lines).strip()))
            heading, lines = line[3:].strip(), []
        elif heading is not None:
            lines.append(line.strip())
    if heading is not None:
        sections.append((heading, " ".join(lines).strip()))
    return sections


def load_chunks(folder: Path, size: int, overlap: int) -> list[Chunk]:
    """Chunk every Markdown note in a folder.

    Args:
        folder: Folder of .md notes. The file stem is the document ID.
        size: Words per chunk.
        overlap: Words shared by neighbouring chunks.

    Returns:
        Chunks in file, section and window order.

    Raises:
        FileNotFoundError: If the folder holds no .md files.
    """
    paths = sorted(folder.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"no .md notes in {folder}")
    chunks: list[Chunk] = []
    for path in paths:
        doc_id = path.stem
        for heading, body in split_sections(path.read_text(encoding="utf-8")):
            section_id = f"{doc_id}#{slugify(heading)}"
            for n, window in enumerate(chunk_words(body, size, overlap)):
                chunks.append(Chunk(f"{section_id}#{n}", section_id, doc_id, heading, window))
    return chunks
