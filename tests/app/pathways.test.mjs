// Unit tests for pathway choice, stage progress and the next lesson.
import assert from "node:assert/strict";
import { test } from "node:test";

import * as paths from "../../site/app/pathways.js";
import * as store from "../../site/app/store.js";

const index = {
  bands: [],
  tracks: [{
    id: "B",
    modules: [
      { id: "B1", tags: [], lessons: [{ id: "B1-L1", exercises: ["a", "b"] }, { id: "B1-L2", exercises: ["c"] }] },
      { id: "B2", tags: [], lessons: [] },
      { id: "B3", tags: [], lessons: [{ id: "B3-L1", exercises: ["d"] }] },
    ],
  }],
  pathways: [
    { id: "first", stages: [{ id: "s1", modules: ["B1", "B2"] }, { id: "s2", modules: ["B3"] }] },
    { id: "second", stages: [{ id: "only", modules: ["B3", "B1"] }] },
  ],
};
const modules = paths.moduleIndex(index);

function pass(state, ...ids) {
  for (const id of ids) store.recordAttempt(state, id, true, 10, "2026-11-03");
}

test("the first pathway is chosen until another is picked", () => {
  const s = store.emptyState();
  assert.equal(paths.chosenPathway(index, s).id, "first");
  paths.choosePathway(s, "second");
  assert.equal(paths.chosenPathway(index, s).id, "second");
  s.settings.pathway = "gone";
  assert.equal(paths.chosenPathway(index, s).id, "first");
});

test("the choice survives an export and import", () => {
  const s = store.emptyState();
  paths.choosePathway(s, "second");
  assert.equal(store.importJson(store.exportJson(s)).settings.pathway, "second");
});

test("stage and pathway progress count exercises, skipping unpublished modules", () => {
  const s = store.emptyState();
  pass(s, "a", "b");
  const [s1, s2] = index.pathways[0].stages;
  assert.deepEqual(paths.stageProgress(s, s1, modules), { done: 2, total: 3, share: 2 / 3 });
  assert.deepEqual(paths.stageProgress(s, s2, modules), { done: 0, total: 1, share: 0 });
  assert.equal(paths.pathwayProgress(s, index.pathways[0], modules).share, 0.5);
});

test("next step follows the pathway order, not the track order", () => {
  const s = store.emptyState();
  assert.equal(paths.nextStep(s, index.pathways[1], modules).lesson.id, "B3-L1");
  pass(s, "d");
  const step = paths.nextStep(s, index.pathways[1], modules);
  assert.equal(step.lesson.id, "B1-L1");
  assert.equal(step.stage.id, "only");
  assert.equal(step.module.id, "B1");
});

test("current stage moves on as stages finish, and stays on the last one at the end", () => {
  const s = store.emptyState();
  const first = index.pathways[0];
  assert.equal(paths.currentStageId(s, first, modules), "s1");
  pass(s, "a", "b", "c");
  assert.equal(paths.currentStageId(s, first, modules), "s2");
  pass(s, "d");
  assert.equal(paths.nextStep(s, first, modules), null);
  assert.equal(paths.currentStageId(s, first, modules), "s2");
});

test("following lesson crosses modules and stages, and is null at the end or outside the pathway", () => {
  const first = index.pathways[0];
  assert.equal(paths.followingLesson(first, modules, "B1-L1").lesson.id, "B1-L2");
  assert.equal(paths.followingLesson(first, modules, "B1-L2").lesson.id, "B3-L1");
  assert.equal(paths.followingLesson(first, modules, "B3-L1"), null);
  assert.equal(paths.followingLesson(first, modules, "Z9-L1"), null);
});
