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

const timed = {
  id: "t",
  start: "2026-12-10",
  phases: [
    { id: "P1", days: [1, 30], modules: ["I1", "A1"] },
    { id: "P2", days: [31, 60], modules: ["A2", "X9"] },
    { id: "P3", days: [61, 90], modules: [] },
  ],
  modules: [
    { id: "I1", hours: 6, lessons: [{ id: "L1" }, { id: "L2" }, { id: "L3" }] },
    { id: "A1", hours: 4, lessons: [{ id: "L3" }, { id: "L4" }] },
    { id: "A2", hours: 5, lessons: [] },
  ],
};

test("countdown settings default to the plan and ignore values that no longer fit", () => {
  assert.deepEqual(role.countdownSettings(timed, undefined), { start: "2026-12-10", through: "P2", by: "start", per_week: 5, home: true });
  const record = { countdown: { start: "2027-02-30", through: "P9", by: "P7", per_week: 9, home: "yes" } };
  assert.deepEqual(role.countdownSettings(timed, record), role.countdownSettings(timed, undefined));
  const one = { ...timed, phases: [timed.phases[0]] };
  assert.equal(role.countdownSettings(one, {}).through, "P1");
});

test("setCountdown checks each setting against the plan", () => {
  const s = store.emptyState();
  role.setCountdown(s, timed, { start: "2027-01-04", through: "P1", by: "P1", per_week: 3, home: false });
  assert.deepEqual(role.countdownSettings(timed, s.roles.t), { start: "2027-01-04", through: "P1", by: "P1", per_week: 3, home: false });
  assert.throws(() => role.setCountdown(s, timed, { start: "4 January" }));
  assert.throws(() => role.setCountdown(s, timed, { through: "P9" }));
  assert.throws(() => role.setCountdown(s, timed, { per_week: 0 }));
  assert.throws(() => role.setCountdown(s, timed, { per_week: 2.5 }));
  assert.throws(() => role.setCountdown(s, timed, { colour: "red" }));
  assert.equal(s.roles.t.countdown.per_week, 3);
});

test("studyDays counts whole weeks and the part week, never more than the days left", () => {
  assert.equal(role.studyDays(0, 5), 0);
  assert.equal(role.studyDays(-3, 5), 0);
  assert.equal(role.studyDays(3, 5), 3);
  assert.equal(role.studyDays(7, 5), 5);
  assert.equal(role.studyDays(33, 5), 4 * 5 + 5);
  assert.equal(role.studyDays(30, 2), 4 * 2 + 2);
  assert.equal(role.studyDays(14, 7), 14);
});

test("countdown counts unique lessons left and the pace to the start date", () => {
  const done = new Set(["L1"]);
  const c = role.countdown(timed, {}, "2026-11-07", (id) => done.has(id));
  assert.equal(c.deadline, "2026-12-10");
  assert.equal(c.daysLeft, 33);
  assert.equal(c.studyDays, 25);
  assert.deepEqual(c.phases, ["P1", "P2"]);
  assert.equal(c.lessonsTotal, 4);
  assert.equal(c.lessonsLeft, 3);
  // I1 has 2 of 3 lessons left (4 h), A1 2 of 2 (4 h), A2 has no lessons (5 h), X9 is unknown.
  assert.equal(c.hoursLeft, 13);
  assert.equal(c.lessonsPerStudyDay, 0.1);
  assert.equal(c.hoursPerStudyDay, 0.5);
  assert.equal(c.status, "running");
});

test("countdown follows your own start date, phase and deadline", () => {
  const record = { countdown: { start: "2027-01-04", through: "P1", by: "P1", per_week: 3 }, done: {} };
  const c = role.countdown(timed, record, "2027-01-04", () => false);
  assert.equal(c.deadline, "2027-02-03");
  assert.equal(c.daysLeft, 30);
  assert.equal(c.studyDays, 4 * 3 + 2);
  assert.equal(c.lessonsLeft, 4);
  assert.equal(c.hoursLeft, 10);
});

test("a ticked assessment clears the hours of a competency with no lessons", () => {
  const all = () => true;
  assert.equal(role.countdown(timed, {}, "2026-11-07", all).status, "running");
  const c = role.countdown(timed, { done: { A2: true } }, "2026-11-07", all);
  assert.equal(c.hoursLeft, 0);
  assert.equal(c.status, "done");
});

test("after the deadline the countdown reports passed, with no pace", () => {
  const c = role.countdown(timed, {}, "2026-12-10", () => false);
  assert.equal(c.daysLeft, 0);
  assert.equal(c.studyDays, 0);
  assert.equal(c.lessonsPerStudyDay, null);
  assert.equal(c.status, "passed");
});
