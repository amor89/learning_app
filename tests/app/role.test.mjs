// Unit tests for role plans: plan days and dates, self-assessment summaries and lesson progress.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import * as role from "../../site/app/role.js";
import * as store from "../../site/app/store.js";

const plan = {
  id: "r",
  start: "2026-12-10",
  streams: ["Infra", "Arch"],
  phases: [
    { id: "P1", name: "Orient", days: [1, 30], modules: ["I1", "A1"] },
    { id: "P2", name: "Design", days: [31, 60], modules: ["A2"] },
  ],
  modules: [
    { id: "I1", stream: "Infra", target: 3 },
    { id: "A1", stream: "Arch", target: 3 },
    { id: "A2", stream: "Arch", target: 4 },
  ],
};

test("plan days count from the start date, which is day 1", () => {
  assert.equal(role.planDay("2026-12-10", "2026-12-10"), 1);
  assert.equal(role.planDay("2026-12-10", "2027-01-08"), 30);
  assert.equal(role.planDay("2026-12-10", "2026-12-01"), -8);
  assert.equal(role.dayToDate("2026-12-10", 30), "2027-01-08");
  assert.deepEqual(role.phaseDates("2026-12-10", plan.phases[1]), { from: "2027-01-09", to: "2027-02-07" });
});

test("currentPhase is the first phase before the start, and none after the end", () => {
  assert.equal(role.currentPhase(plan, "2026-11-06").id, "P1");
  assert.equal(role.currentPhase(plan, "2027-01-08").id, "P1");
  assert.equal(role.currentPhase(plan, "2027-01-09").id, "P2");
  assert.equal(role.currentPhase(plan, "2027-06-01"), null);
});

test("levels are 1 to 4 and record the day you assessed them", () => {
  const s = store.emptyState();
  role.setLevel(s, "r", "I1", 2, "2026-11-06");
  assert.equal(s.roles.r.levels.I1, 2);
  assert.equal(s.roles.r.assessed.I1, "2026-11-06");
  assert.throws(() => role.setLevel(s, "r", "I1", 5, "d"));
  assert.throws(() => role.setLevel(s, "r", "I1", 0, "d"));
});

test("toggle sets and clears done marks, and rejects unknown records", () => {
  const s = store.emptyState();
  role.toggle(s, "r", "done", "I1", true);
  role.toggle(s, "r", "phases", "P1", true);
  assert.deepEqual(s.roles.r.done, { I1: true });
  role.toggle(s, "r", "done", "I1", false);
  assert.deepEqual(s.roles.r.done, {});
  assert.throws(() => role.toggle(s, "r", "nope", "x", true));
});

test("streamSummary compares your mean level with the mean target, per stream", () => {
  const record = { levels: { A1: 3, A2: 2 } };
  const [infra, arch] = role.streamSummary(plan, record);
  assert.deepEqual(infra, { stream: "Infra", modules: 1, rated: 0, level: null, target: 3, below: [] });
  assert.deepEqual(arch, { stream: "Arch", modules: 2, rated: 2, level: 2.5, target: 3.5, below: ["A2"] });
  assert.equal(role.levelGap(record, plan.modules[2]), 2);
  assert.equal(role.levelGap(record, plan.modules[0]), null);
});

test("lessonProgress counts completed lessons", () => {
  const s = store.emptyState();
  const meta = new Map([["L1", { id: "L1", exercises: ["e1"] }], ["L2", { id: "L2", exercises: ["e2"] }]]);
  s.ex.e1 = { attempts: 1, passed: "d", solution: false, hints: 0, score: 1 };
  assert.deepEqual(role.lessonProgress(s, [{ id: "L1" }, { id: "L2" }, { id: "missing" }], meta), { done: 1, total: 3 });
});

test("old progress exports gain an empty roles record", () => {
  const { roles, ...old } = store.emptyState();
  assert.deepEqual(store.migrate(old).roles, {});
});

test("the built role plan links to lessons that exist and a pathway with one stage per phase", () => {
  const bank = JSON.parse(readFileSync(new URL("../../site/content/roles.json", import.meta.url), "utf8"));
  const index = JSON.parse(readFileSync(new URL("../../site/content/index.json", import.meta.url), "utf8"));
  const lessons = new Set(index.tracks.flatMap((t) => t.modules.flatMap((m) => m.lessons.map((l) => l.id))));
  for (const r of bank.roles) {
    const pathway = index.pathways.find((p) => p.id === r.pathway);
    assert.equal(pathway.stages.length, r.phases.length, r.id);
    for (const m of r.modules) for (const l of m.lessons) assert.ok(lessons.has(l.id), `${m.id} ${l.id}`);
    assert.ok(index.roles.some((x) => x.id === r.id));
  }
});
