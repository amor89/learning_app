// Unit tests for progress storage, XP, streaks, badges and SM-2 review.
import assert from "node:assert/strict";
import { test } from "node:test";

import * as store from "../../site/app/store.js";

const index = {
  bands: [{ id: "prereq", label: "Prerequisite" }, { id: "M1-3", label: "Months 1 to 3" }],
  tracks: [{
    id: "B",
    modules: [
      { id: "B1", tags: ["prereq"], lessons: [{ id: "B1-L1", exercises: ["B1-L1-E1", "B1-L1-E2"] }] },
      { id: "B2", tags: ["prereq", "M1-3"], lessons: [] },
    ],
  }],
};

test("first pass earns XP once, reduced by hints", () => {
  const s = store.emptyState();
  store.recordHint(s, "x");
  assert.equal(store.recordAttempt(s, "x", false, 40, "2026-09-01"), 0);
  assert.equal(store.recordAttempt(s, "x", true, 40, "2026-09-01"), 30);
  assert.equal(store.recordAttempt(s, "x", true, 40, "2026-09-01"), 0);
  assert.equal(s.xp, 30);
  assert.equal(s.ex.x.attempts, 3);
});

test("passing after seeing the solution earns the minimum share", () => {
  const s = store.emptyState();
  store.recordAttempt(s, "x", false, 40, "2026-09-01");
  store.recordSolutionSeen(s, "x");
  assert.equal(store.recordAttempt(s, "x", true, 40, "2026-09-01"), 10);
});

test("streak counts consecutive days and resets after a gap", () => {
  const s = store.emptyState();
  store.markActive(s, 0, "2026-09-01");
  store.markActive(s, 0, "2026-09-02");
  store.markActive(s, 0, "2026-09-02");
  assert.equal(s.streak.current, 2);
  store.markActive(s, 0, "2026-09-05");
  assert.equal(s.streak.current, 1);
  assert.equal(s.streak.best, 2);
  assert.equal(store.currentStreak(s, "2026-09-07"), 0);
});

test("streak crosses a month boundary", () => {
  const s = store.emptyState();
  store.markActive(s, 0, "2026-09-30");
  store.markActive(s, 0, "2026-10-01");
  assert.equal(s.streak.current, 2);
});

test("badge needs every lesson of a module complete, and never for an empty module", () => {
  const s = store.emptyState();
  store.recordAttempt(s, "B1-L1-E1", true, 10);
  assert.deepEqual(store.awardBadges(s, index), []);
  store.recordAttempt(s, "B1-L1-E2", false, 10);
  store.recordSolutionSeen(s, "B1-L1-E2");
  assert.deepEqual(store.awardBadges(s, index).map((m) => m.id), ["B1"]);
  assert.deepEqual(store.awardBadges(s, index), []);
});

test("mastery averages scores; bands aggregate their modules", () => {
  const s = store.emptyState();
  store.recordAttempt(s, "B1-L1-E1", true, 10);
  assert.equal(store.masteryOf(s, ["B1-L1-E1", "B1-L1-E2"]), 0.5);
  assert.equal(store.masteryOf(s, []), null);
  const bands = store.bandMastery(s, index);
  assert.equal(bands[0].mastery, 0.5);
  assert.equal(bands[1].mastery, null);
});

test("SM-2 intervals grow and reset on again", () => {
  let card = { ef: 2.5, n: 0, interval: 0, due: "2026-09-01" };
  card = store.reviewCard(card, "good", "2026-09-01");
  assert.equal(card.interval, 1);
  card = store.reviewCard(card, "good", "2026-09-02");
  assert.equal(card.interval, 6);
  card = store.reviewCard(card, "good", "2026-09-08");
  assert.equal(card.interval, 15);
  assert.equal(card.due, "2026-09-23");
  card = store.reviewCard(card, "again", "2026-09-23");
  assert.equal(card.interval, 1);
  assert.ok(card.ef >= 1.3);
});

test("completing a lesson adds its cards, due today", () => {
  const s = store.emptyState();
  store.completeLesson(s, "B1-L1", ["B1-L1#0", "B1-L1#1"], "2026-09-01");
  assert.deepEqual(store.dueCards(s, "2026-09-01"), ["B1-L1#0", "B1-L1#1"]);
});

test("export and import round-trip; foreign files are rejected", () => {
  const s = store.emptyState();
  store.recordAttempt(s, "x", true, 20, "2026-09-01");
  assert.deepEqual(store.importJson(store.exportJson(s)), s);
  assert.throws(() => store.importJson('{"v": 99}'), /not a progress export/);
});
