// Unit tests for the placement quiz: grading, the skip decision and the route past a skipped module.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import * as paths from "../../site/app/pathways.js";
import * as pl from "../../site/app/placement.js";
import * as store from "../../site/app/store.js";

const L1 = { id: "B0-L1", title: "One" };
const L2 = { id: "B0-L2", title: "Two" };
const quiz = {
  track: "B",
  module: { id: "B0", title: "Start" },
  next: { id: "B1", title: "Next" },
  pass_mark: 3,
  lessons: [L1, L2],
  questions: [
    { id: "B-1", lessons: [L1], answer: "a" },
    { id: "B-2", lessons: [L1], answer: "b" },
    { id: "B-3", lessons: [L2], answer: "c" },
    { id: "B-4", lessons: [L2], answer: "d" },
  ],
};

test("gradeQuiz counts right answers and lists the lessons behind misses, in module order", () => {
  const all = pl.gradeQuiz(quiz, { "B-1": "a", "B-2": "b", "B-3": "c", "B-4": "d" });
  assert.deepEqual(all, { score: 4, total: 4, passed: true, missed: [], review: [] });
  const some = pl.gradeQuiz(quiz, { "B-1": "a", "B-2": "b", "B-3": "c", "B-4": "a" });
  assert.equal(some.passed, true);
  assert.deepEqual(some.review, [L2]);
  const few = pl.gradeQuiz(quiz, { "B-1": "x", "B-3": "c", "B-4": "a" });
  assert.equal(few.score, 1);
  assert.equal(few.passed, false);
  assert.deepEqual(few.missed, ["B-1", "B-2", "B-4"]);
  assert.deepEqual(few.review, [L1, L2]);
});

test("unanswered counts the questions with no choice", () => {
  assert.equal(pl.unanswered(quiz, { "B-1": "a" }), 3);
  assert.equal(pl.unanswered(quiz, {}), 4);
});

test("only a passed quiz lets you skip, and a retake clears the skip", () => {
  const s = store.emptyState();
  assert.equal(pl.setSkipped(s, "B", true), false, "no result yet");
  pl.recordPlacement(s, quiz, pl.gradeQuiz(quiz, {}), "2026-11-06");
  assert.equal(pl.setSkipped(s, "B", true), false, "a failed quiz cannot skip");
  pl.recordPlacement(s, quiz, pl.gradeQuiz(quiz, { "B-1": "a", "B-2": "b", "B-3": "c" }), "2026-11-07");
  assert.equal(pl.setSkipped(s, "B", true), true);
  assert.deepEqual([...store.skippedModules(s)], ["B0"]);
  pl.recordPlacement(s, quiz, pl.gradeQuiz(quiz, { "B-1": "a", "B-2": "b", "B-3": "c", "B-4": "d" }), "2026-11-08");
  assert.equal(pl.placementFor(s, "B").skipped, false);
  assert.equal(store.skippedModules(s).size, 0);
});

test("old progress exports gain an empty placement record", () => {
  const { placement, ...old } = store.emptyState();
  assert.deepEqual(store.migrate(old).placement, {});
});

test("nextStep passes over a skipped module", () => {
  const index = {
    tracks: [{ id: "B", modules: [
      { id: "B0", lessons: [{ id: "B0-L1", exercises: ["x"] }] },
      { id: "B1", lessons: [{ id: "B1-L1", exercises: ["y"] }] },
    ] }],
  };
  const pathway = { id: "p", stages: [{ id: "s", modules: ["B0", "B1"] }] };
  const modules = paths.moduleIndex(index);
  const s = store.emptyState();
  assert.equal(paths.nextStep(s, pathway, modules).lesson.id, "B0-L1");
  s.placement = { B: { module: "B0", passed: true, skipped: true } };
  assert.equal(paths.nextStep(s, pathway, modules).lesson.id, "B1-L1");
  assert.equal(paths.currentStageId(s, pathway, modules), "s");
});

test("the built quizzes have ten questions with valid keys", () => {
  const bank = JSON.parse(readFileSync(new URL("../../site/content/placement.json", import.meta.url), "utf8"));
  assert.deepEqual(bank.quizzes.map((q) => q.track), ["A", "B", "C", "D"]);
  for (const q of bank.quizzes) {
    assert.equal(q.questions.length, 10);
    assert.ok(q.pass_mark > 0 && q.next.id !== q.module.id, q.track);
    for (const item of q.questions) assert.ok(item.options.some((o) => o.id === item.answer), item.id);
  }
});

test("firstUnanswered points at the first question without an answer", () => {
  const quiz = { questions: [{ id: "q1" }, { id: "q2" }, { id: "q3" }] };
  assert.equal(pl.firstUnanswered(quiz, {}), 0);
  assert.equal(pl.firstUnanswered(quiz, { q1: "a", q3: "b" }), 1);
  assert.equal(pl.firstUnanswered(quiz, { q1: "a", q2: "b", q3: "c" }), -1);
});
