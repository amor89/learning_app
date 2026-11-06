"""Load and validate every content file under ``content/``."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from learnkit.models import (
    InterviewIndex,
    InterviewTask,
    InterviewTopic,
    Lesson,
    ModuleMeta,
    Pathway,
    Pathways,
    Roadmap,
    TheoryFile,
    TheoryQuestion,
    Track,
)

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


@dataclass
class ModuleContent:
    """A module's metadata with the lessons written so far, in order."""

    meta: ModuleMeta
    track_id: str
    lessons: list[Lesson] = field(default_factory=list)


@dataclass
class Course:
    """Everything the app and handbook builds need."""

    roadmap: Roadmap
    tracks: list[Track]
    modules: dict[str, ModuleContent]
    pathways: list[Pathway] = field(default_factory=list)

    def lessons(self) -> list[Lesson]:
        """Every lesson in syllabus order."""
        return [lesson for module in self.modules.values() for lesson in module.lessons]

    def track_modules(self, track_id: str) -> list[ModuleContent]:
        """Modules of one track in syllabus order."""
        return [m for m in self.modules.values() if m.track_id == track_id]


def read_yaml(path: Path) -> Any:
    """Read one YAML file with the safe loader."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_lesson(path: Path) -> Lesson:
    """Validate one lesson file.

    Raises:
        ValueError: If the file id does not match the file name.
    """
    lesson = Lesson.model_validate(read_yaml(path))
    if lesson.id != path.stem:
        raise ValueError(f"{path}: id {lesson.id} does not match file name")
    return lesson


def load_course(content_dir: Path = CONTENT_DIR) -> Course:
    """Load the roadmap, every track and every lesson.

    Args:
        content_dir: Root of the content tree.

    Returns:
        The validated course.

    Raises:
        ValueError: If a lesson sits in a folder that is not a module of its track,
            or a module uses a tag the roadmap does not define.
    """
    roadmap = Roadmap.model_validate(read_yaml(content_dir / "roadmap.yaml"))
    band_ids = {band.id for band in roadmap.bands}
    tracks: list[Track] = []
    modules: dict[str, ModuleContent] = {}
    for track_file in sorted(content_dir.glob("tracks/*/track.yaml")):
        track = Track.model_validate(read_yaml(track_file))
        tracks.append(track)
        for meta in track.modules:
            unknown = set(meta.tags) - band_ids
            if unknown:
                raise ValueError(f"{meta.id}: unknown roadmap tags {unknown}")
            modules[meta.id] = ModuleContent(meta, track.id)
        for module_dir in sorted(p for p in track_file.parent.iterdir() if p.is_dir()):
            if module_dir.name not in modules:
                raise ValueError(f"{module_dir}: not a module of track {track.id}")
            for lesson_file in sorted(module_dir.glob("*.yaml")):
                lesson = load_lesson(lesson_file)
                if not lesson.id.startswith(f"{module_dir.name}-"):
                    raise ValueError(f"{lesson_file}: lesson id must start with module id")
                modules[module_dir.name].lessons.append(lesson)
    pathways = load_pathways(content_dir / "pathways.yaml", set(modules))
    return Course(roadmap, tracks, modules, pathways)


def load_pathways(path: Path, module_ids: set[str]) -> list[Pathway]:
    """Validate the pathways against the modules that exist.

    Raises:
        ValueError: If pathway ids repeat, a pathway names a module that does not
            exist, or a module sits in no pathway.
    """
    pathways = Pathways.model_validate(read_yaml(path)).pathways
    ids = [p.id for p in pathways]
    if len(ids) != len(set(ids)):
        raise ValueError("pathway ids must be unique")
    listed = {m for p in pathways for s in p.stages for m in s.modules}
    unknown = sorted(listed - module_ids)
    if unknown:
        raise ValueError(f"pathways name unknown modules: {unknown}")
    orphans = sorted(module_ids - listed)
    if orphans:
        raise ValueError(f"modules in no pathway: {orphans}")
    return pathways


@dataclass
class Interview:
    """The interview practice bank: theory questions by topic, and coding tasks."""

    topics: list[InterviewTopic]
    questions: dict[str, list[TheoryQuestion]]
    tasks: list[InterviewTask]

    def all_questions(self) -> list[TheoryQuestion]:
        """Every theory question in topic order."""
        return [q for topic in self.topics for q in self.questions[topic.id]]


def load_interview(course: Course, content_dir: Path = CONTENT_DIR) -> Interview:
    """Load and validate content/interview/.

    Args:
        course: The loaded course, to check the lessons each item names.
        content_dir: Root of the content tree.

    Returns:
        The validated interview bank.

    Raises:
        ValueError: If a topic has no question file, a file has no topic, a task
            file is missing or unlisted, or an item names a lesson that does not exist.
    """
    root = content_dir / "interview"
    index = InterviewIndex.model_validate(read_yaml(root / "index.yaml"))
    topic_ids = [t.id for t in index.topics]
    files = {path.stem: path for path in sorted((root / "theory").glob("*.yaml"))}
    if sorted(files) != sorted(topic_ids):
        raise ValueError(f"theory files {sorted(files)} do not match topics {sorted(topic_ids)}")
    questions: dict[str, list[TheoryQuestion]] = {}
    for topic in index.topics:
        theory = TheoryFile.model_validate(read_yaml(files[topic.id]))
        if theory.topic != topic.id:
            raise ValueError(f"{files[topic.id]}: topic {theory.topic} does not match file name")
        questions[topic.id] = theory.questions
    task_files = {path.stem: path for path in sorted((root / "tasks").glob("*.yaml"))}
    if sorted(task_files) != sorted(index.tasks) or len(set(index.tasks)) != len(index.tasks):
        raise ValueError(f"task files {sorted(task_files)} do not match index {index.tasks}")
    tasks = [InterviewTask.model_validate(read_yaml(task_files[t])) for t in index.tasks]
    for task, name in zip(tasks, index.tasks, strict=True):
        if task.id != name:
            raise ValueError(f"{task_files[name]}: id {task.id} does not match file name")
    lesson_ids = {lesson.id for lesson in course.lessons()}
    items: list[TheoryQuestion | InterviewTask] = [
        *(q for qs in questions.values() for q in qs),
        *tasks,
    ]
    for item in items:
        unknown = sorted(set(item.lessons) - lesson_ids)
        if unknown:
            raise ValueError(f"{item.id}: names lessons that do not exist: {unknown}")
    return Interview(index.topics, questions, tasks)
