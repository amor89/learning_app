"""Quality gates for role plans in content/roles/.

- The loader checks lessons, prerequisites, phases and the pathway (it runs here).
- The role's pathway has one stage per phase, listing exactly the modules that
  teach that phase's competencies, so the dashboard follows the plan.
- Day ranges run on from one phase to the next.
"""

from __future__ import annotations

import pytest

from learnkit.loader import load_course, load_roles, role_stage_modules
from learnkit.models import Role

COURSE = load_course()
ROLES = load_roles(COURSE)


def test_there_is_a_role() -> None:
    assert ROLES


@pytest.mark.parametrize("role", ROLES, ids=lambda r: r.id)
def test_pathway_follows_the_phases(role: Role) -> None:
    pathway = next(p for p in COURSE.pathways if p.id == role.pathway)
    assert len(pathway.stages) == len(role.phases)
    expected = role_stage_modules(role, COURSE)
    for stage, phase, modules in zip(pathway.stages, role.phases, expected, strict=True):
        assert stage.modules == modules, f"{stage.id} should list {modules} for {phase.id}"


@pytest.mark.parametrize("role", ROLES, ids=lambda r: r.id)
def test_phase_days_run_on(role: Role) -> None:
    assert role.phases[0].days[0] == 1
    for before, after in zip(role.phases, role.phases[1:], strict=False):
        assert after.days[0] == before.days[1] + 1, (
            f"{after.id} should start the day after {before.id}"
        )


@pytest.mark.parametrize("role", ROLES, ids=lambda r: r.id)
def test_every_stream_has_a_module(role: Role) -> None:
    assert {m.stream for m in role.modules} == set(role.streams)
