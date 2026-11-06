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
    Months,
    Pathway,
    Pathways,
    PlacementQuiz,
    Roadmap,
    Role,
    Stage,
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


def load_placement(course: Course, content_dir: Path = CONTENT_DIR) -> list[PlacementQuiz]:
    """Load content/placement/<track>.yaml, one quiz per track, in track order.

    Raises:
        ValueError: If a file name does not match its track, the quiz's module is not
            the first module of the track, or a question names a lesson outside it.
    """
    quizzes: list[PlacementQuiz] = []
    order = {track.id: i for i, track in enumerate(course.tracks)}
    for path in sorted((content_dir / "placement").glob("*.yaml")):
        quiz = PlacementQuiz.model_validate(read_yaml(path))
        track = next((t for t in course.tracks if t.id == quiz.track), None)
        if track is None or path.stem != quiz.track:
            raise ValueError(f"{path}: track {quiz.track} does not match a track and the file name")
        if track.modules[0].id != quiz.module:
            raise ValueError(f"{path}: {quiz.module} is not the first module of track {track.id}")
        lesson_ids = {lesson.id for lesson in course.modules[quiz.module].lessons}
        for question in quiz.questions:
            outside = sorted(set(question.lessons) - lesson_ids)
            if outside:
                raise ValueError(f"{question.id}: names lessons outside {quiz.module}: {outside}")
        quizzes.append(quiz)
    return sorted(quizzes, key=lambda q: order[q.track])


@dataclass
class MonthStage:
    """One roadmap month: a pathway stage with its modules that have lessons."""

    pathway: Pathway
    stage: Stage
    modules: list[ModuleContent]

    @property
    def stem(self) -> str:
        """File stem of the month's quick reference."""
        return f"quickref-{self.stage.id}"


def load_months(course: Course, content_dir: Path = CONTENT_DIR) -> list[MonthStage]:
    """Load content/months.yaml and resolve each stage against the pathways.

    Raises:
        ValueError: If the pathway or a stage does not exist, or a stage has no lessons yet.
    """
    months = Months.model_validate(read_yaml(content_dir / "months.yaml"))
    pathway = next((p for p in course.pathways if p.id == months.pathway), None)
    if pathway is None:
        raise ValueError(f"months.yaml: pathway {months.pathway} does not exist")
    stages = {stage.id: stage for stage in pathway.stages}
    out: list[MonthStage] = []
    for stage_id in months.stages:
        if stage_id not in stages:
            raise ValueError(f"months.yaml: stage {stage_id} is not in {pathway.id}")
        stage = stages[stage_id]
        modules = [course.modules[m] for m in stage.modules if course.modules[m].lessons]
        if not modules:
            raise ValueError(f"months.yaml: stage {stage_id} has no lessons yet")
        out.append(MonthStage(pathway, stage, modules))
    return out


def load_roles(course: Course, content_dir: Path = CONTENT_DIR) -> list[Role]:
    """Load content/roles/*.yaml and check them against the course.

    Raises:
        ValueError: If a file name does not match its id, a module names a lesson
            that does not exist, or the role's pathway does not exist.
    """
    lesson_ids = {lesson.id for lesson in course.lessons()}
    pathway_ids = {p.id for p in course.pathways}
    roles = []
    for path in sorted((content_dir / "roles").glob("*.yaml")):
        role = Role.model_validate(read_yaml(path))
        if role.id != path.stem:
            raise ValueError(f"{path}: id {role.id} does not match file name")
        if role.pathway not in pathway_ids:
            raise ValueError(f"{role.id}: pathway {role.pathway} does not exist")
        for module in role.modules:
            unknown = sorted(set(module.lessons) - lesson_ids)
            if unknown:
                raise ValueError(f"{module.id}: names lessons that do not exist: {unknown}")
        roles.append(role)
    return roles


def role_stage_modules(role: Role, course: Course) -> list[list[str]]:
    """The app modules each phase draws on, in the order the plan lists them, each once.

    A module appears in the first phase that uses one of its lessons. The role's
    pathway lists exactly these, so the dashboard follows the phases.
    """
    module_of = {lesson.id: m.meta.id for m in course.modules.values() for lesson in m.lessons}
    by_id = {m.id: m for m in role.modules}
    seen: set[str] = set()
    stages = []
    for phase in role.phases:
        lessons = [lesson for mid in phase.modules for lesson in by_id[mid].lessons]
        modules = []
        for lesson in lessons:
            module = module_of[lesson]
            if module not in seen:
                seen.add(module)
                modules.append(module)
        stages.append(modules)
    return stages
