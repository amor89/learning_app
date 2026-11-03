"""Pathways name real modules, cover every module, and never repeat one within a pathway."""

from pathlib import Path

import pytest
import yaml

from learnkit.loader import load_course, load_pathways


def _write(tmp_path: Path, stages: list[dict[str, object]], pid: str = "p") -> Path:
    path = tmp_path / "pathways.yaml"
    pathway = {"id": pid, "title": "T", "summary": "S", "stages": stages}
    path.write_text(yaml.safe_dump({"pathways": [pathway]}), encoding="utf-8")
    return path


def _stage(sid: str, modules: list[str]) -> dict[str, object]:
    return {"id": sid, "title": sid, "summary": "s", "modules": modules}


def test_course_pathways_cover_every_module() -> None:
    course = load_course()
    listed = {m for p in course.pathways for s in p.stages for m in s.modules}
    assert listed == set(course.modules)
    assert course.pathways[0].id == "ds-roadmap"


def test_roadmap_pathway_follows_the_bands() -> None:
    course = load_course()
    roadmap = next(p for p in course.pathways if p.id == "ds-roadmap")
    for stage in roadmap.stages:
        if stage.id.startswith("m"):
            band = "M" + stage.id[1:]
            for module_id in stage.modules:
                assert band in course.modules[module_id].meta.tags, (stage.id, module_id)


def test_valid_file_loads(tmp_path: Path) -> None:
    path = _write(tmp_path, [_stage("a", ["B1"]), _stage("b", ["B2"])])
    assert [s.id for s in load_pathways(path, {"B1", "B2"})[0].stages] == ["a", "b"]


def test_unknown_module_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown modules"):
        load_pathways(_write(tmp_path, [_stage("a", ["B1", "B99"])]), {"B1"})


def test_orphan_module_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no pathway"):
        load_pathways(_write(tmp_path, [_stage("a", ["B1"])]), {"B1", "B2"})


def test_module_twice_in_one_pathway_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="listed twice"):
        load_pathways(_write(tmp_path, [_stage("a", ["B1"]), _stage("b", ["B1"])]), {"B1"})


def test_repeated_stage_id_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="stage ids"):
        load_pathways(_write(tmp_path, [_stage("a", ["B1"]), _stage("a", ["B2"])]), {"B1", "B2"})
