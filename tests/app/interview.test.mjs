// Unit tests for interview practice: question order, scoring, drills and the task clock.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import * as iv from "../../site/app/interview.js";
import * as store from "../../site/app/store.js";

const mcq = (id, topic) => ({ id, topic, kind: "mcq", answer: "b", options: [{ id: "a" }, { id: "b" }, { id: "c" }], points_html: [] });
const open = (id, topic) => ({ id, topic, kind: "open", answer: null, options: [], points_html: ["one", "two", "three", "four"] });
const QUESTIONS = [mcq("s-1", "s"), open("s-2", "s"), mcq("s-3", "s"), open("t-1", "t"), mcq("t-2", "t")];

test("an empty state carries an interview record, and old exports gain one", () => {
  const s = store.emptyState();
  assert.deepEqual(Object.keys(s.interview).sort(), ["drills", "prefs", "tasks", "theory"]);
  const { interview, ...old } = s;
  const migrated = store.migrate(old);
  assert.deepEqual(iv.interviewState(migrated).theory, {});
});

test("shuffle is stable for a seed and keeps every item", () => {
  const items = ["a", "b", "c", "d", "e"];
  assert.deepEqual(iv.shuffle(items, "x"), iv.shuffle(items, "x"));
  assert.deepEqual([...iv.shuffle(items, "x")].sort(), items);
  assert.notDeepEqual(iv.shuffle(items, "x"), iv.shuffle(items, "y"));
});

test("pickQuestions filters by topic and caps the count", () => {
  assert.deepEqual(iv.pickQuestions(QUESTIONS, {}, { topic: "t", count: 10, seed: "1" }).map((q) => q.id).sort(), ["t-1", "t-2"]);
  assert.equal(iv.pickQuestions(QUESTIONS, {}, { topic: "all", count: 3, seed: "1" }).length, 3);
});

test("pickQuestions asks unseen questions first, then the weakest, then the oldest", () => {
  const theory = {
    "s-1": { seen: 1, last: 1, best: 1, day: "2026-11-01" },
    "s-2": { seen: 1, last: 0.25, best: 0.25, day: "2026-11-03" },
    "s-3": { seen: 2, last: 0.25, best: 1, day: "2026-11-02" },
    "t-2": { seen: 1, last: 0, best: 0, day: "2026-11-04" },
  };
  const order = iv.pickQuestions(QUESTIONS, theory, { count: 5, seed: "z" }).map((q) => q.id);
  assert.deepEqual(order, ["t-1", "t-2", "s-3", "s-2", "s-1"]);
});

test("scoreAnswer marks multiple choice and counts ticked points", () => {
  assert.equal(iv.scoreAnswer(QUESTIONS[0], { choice: "b" }), 1);
  assert.equal(iv.scoreAnswer(QUESTIONS[0], { choice: "a" }), 0);
  assert.equal(iv.scoreAnswer(QUESTIONS[0], {}), 0);
  assert.equal(iv.scoreAnswer(QUESTIONS[1], { ticks: [0, 2, 2] }), 0.5);
  assert.equal(iv.scoreAnswer(QUESTIONS[1], { ticks: [9, -1] }), 0);
  assert.equal(iv.scoreAnswer(QUESTIONS[1], { ticks: [0, 1, 2, 3] }), 1);
});

test("recordTheory keeps the last and best score, and topicProgress averages the last", () => {
  const s = store.emptyState();
  iv.recordTheory(s, "s-1", 1, "2026-11-01");
  const r = iv.recordTheory(s, "s-1", 0.5, "2026-11-02");
  assert.deepEqual(r, { seen: 2, last: 0.5, best: 1, day: "2026-11-02" });
  iv.recordTheory(s, "s-2", 0, "2026-11-02");
  assert.deepEqual(iv.topicProgress(QUESTIONS, s.interview.theory, "s"), { answered: 2, total: 3, mean: 0.25 });
  assert.equal(iv.topicProgress(QUESTIONS, s.interview.theory, "t").mean, null);
});

test("recordDrill keeps the most recent drills only", () => {
  const s = store.emptyState();
  for (let i = 0; i < iv.MAX_DRILLS_KEPT + 5; i += 1) iv.recordDrill(s, { day: `d${i}`, topic: "all", count: 5, total: 3 });
  assert.equal(s.interview.drills.length, iv.MAX_DRILLS_KEPT);
  assert.equal(s.interview.drills.at(-1).day, `d${iv.MAX_DRILLS_KEPT + 4}`);
  assert.deepEqual(iv.drillScore([{ score: 1 }, { score: 0.5 }]), { total: 1.5, count: 2, share: 0.75 });
  assert.deepEqual(iv.drillScore([]), { total: 0, count: 0, share: 0 });
});

test("formatClock shows minutes and seconds", () => {
  assert.equal(iv.formatClock(0), "0:00");
  assert.equal(iv.formatClock(7_900), "0:07");
  assert.equal(iv.formatClock(90_000), "1:30");
  assert.equal(iv.formatClock(25 * 60_000), "25:00");
  assert.equal(iv.formatClock(-65_000), "-1:05");
});

test("a task run times from the start and stops at the first pass", () => {
  const s = store.emptyState();
  const run = iv.startRun(s, "split", "starter", 1_000);
  assert.equal(iv.elapsed(run, 61_000), 60_000);
  assert.equal(iv.recordCheck(s, "split", false, 600_000, "2026-11-06", 31_000), null);
  const pass = iv.recordCheck(s, "split", true, 600_000, "2026-11-06", 121_000);
  assert.deepEqual(pass, { ms: 120_000, over: false, clean: true, best: true });
  assert.equal(iv.elapsed(run, 999_999), 120_000, "the clock stops at the pass");
  assert.equal(iv.recordCheck(s, "split", true, 600_000, "2026-11-06", 200_000), null, "a second pass changes nothing");
  const record = iv.taskRecord(s, "split");
  assert.equal(record.attempts, 3);
  assert.equal(record.passes, 1);
  assert.equal(record.best.ms, 120_000);
});

test("only a faster clean pass replaces the best time", () => {
  const s = store.emptyState();
  iv.startRun(s, "t", "", 0);
  iv.recordCheck(s, "t", true, 60_000, "d1", 50_000);
  iv.startRun(s, "t", "", 0);
  const slower = iv.recordCheck(s, "t", true, 60_000, "d2", 90_000);
  assert.equal(slower.best, false);
  assert.equal(slower.over, true);
  const run = iv.startRun(s, "t", "", 0);
  iv.useHint(run);
  iv.revealSolution(run, 10_000);
  const viewed = iv.recordCheck(s, "t", true, 60_000, "d3", 20_000);
  assert.deepEqual(viewed, { ms: 10_000, over: false, clean: false, best: false });
  assert.equal(iv.taskRecord(s, "t").best.ms, 50_000);
  assert.equal(iv.taskRecord(s, "t").passes, 2);
});

test("hints stop at three", () => {
  const run = iv.startRun(store.emptyState(), "t", "", 0);
  for (let i = 0; i < 5; i += 1) iv.useHint(run);
  assert.equal(run.hints, iv.MAX_HINTS);
});

test("taskStatus describes each state", () => {
  assert.deepEqual(iv.taskStatus(undefined, 60_000), { text: "Not tried", ok: false });
  const s = store.emptyState();
  iv.startRun(s, "t", "", 0);
  assert.equal(iv.taskStatus(iv.taskRecord(s, "t"), 60_000).text, "Clock running");
  iv.recordCheck(s, "t", false, 60_000, "d", 5_000);
  iv.revealSolution(s.interview.tasks.t.run, 6_000);
  assert.equal(iv.taskStatus(iv.taskRecord(s, "t"), 60_000).text, "Not passed yet");
  const run = iv.startRun(s, "t", "", 0);
  iv.useHint(run);
  run.reminder = true;
  iv.recordCheck(s, "t", true, 60_000, "d", 75_000);
  assert.deepEqual(iv.taskStatus(iv.taskRecord(s, "t"), 60_000), { text: "Best 1:15, over time (1 hint, reminder)", ok: false });
});

test("the built interview bank has the fields the views read", () => {
  const bank = JSON.parse(readFileSync(new URL("../../site/content/interview.json", import.meta.url), "utf8"));
  assert.ok(bank.topics.length > 0 && bank.tasks.length > 0);
  const topics = new Set(bank.topics.map((t) => t.id));
  for (const q of bank.questions) {
    assert.ok(topics.has(q.topic), q.id);
    assert.ok(q.seconds > 0 && q.question_html && q.model_answer_html && q.lessons.length, q.id);
    if (q.kind === "mcq") assert.ok(q.options.some((o) => o.id === q.answer), q.id);
    else assert.ok(q.points_html.length >= 2, q.id);
  }
  for (const t of bank.tasks) {
    assert.ok(t.minutes > 0 && t.starter && t.checker.kind === "python" && t.hints_html.length === 3, t.id);
    assert.ok(t.follow_ups.length >= 2 && t.brief.must_html.length > 0, t.id);
  }
});
