// Unit tests for the work log: adding, checking, listing, deleting and exporting entries.
import assert from "node:assert/strict";
import { test } from "node:test";

import * as store from "../../site/app/store.js";
import * as log from "../../site/app/worklog.js";

test("a new progress state has an empty work log, and old exports gain one", () => {
  assert.deepEqual(store.emptyState().worklog, { entries: [], seq: 0 });
  const { worklog, ...old } = store.emptyState();
  assert.deepEqual(store.migrate(old).worklog, { entries: [], seq: 0 });
});

test("addEntry trims text, numbers entries and keeps the phase", () => {
  const s = store.emptyState();
  const a = log.addEntry(s, { day: "2026-12-14", kind: "win", text: "  Payroll source mapped  ", impact: " 3 reports fed ", phase: "P1" });
  const b = log.addEntry(s, { day: "2026-12-15", kind: "lesson", text: "Ask owners first" });
  assert.deepEqual(a, { id: "w1", day: "2026-12-14", kind: "win", text: "Payroll source mapped", impact: "3 reports fed", phase: "P1" });
  assert.equal(b.id, "w2");
  assert.equal(b.phase, null);
  assert.equal(b.impact, "");
  assert.equal(s.worklog.seq, 2);
});

test("addEntry rejects a bad date, kind, empty or long text, and a bad phase", () => {
  const s = store.emptyState();
  assert.throws(() => log.addEntry(s, { day: "2026-02-30", kind: "win", text: "x" }));
  assert.throws(() => log.addEntry(s, { day: "14/12/2026", kind: "win", text: "x" }));
  assert.throws(() => log.addEntry(s, { day: "2026-12-14", kind: "brag", text: "x" }));
  assert.throws(() => log.addEntry(s, { day: "2026-12-14", kind: "win", text: "   " }));
  assert.throws(() => log.addEntry(s, { day: "2026-12-14", kind: "win", text: "x".repeat(log.MAX_TEXT + 1) }));
  assert.throws(() => log.addEntry(s, { day: "2026-12-14", kind: "win", text: "x", phase: "" }));
  assert.equal(s.worklog.entries.length, 0);
});

test("listEntries puts the newest day first, then the latest added, and filters by kind", () => {
  const s = store.emptyState();
  log.addEntry(s, { day: "2026-12-14", kind: "win", text: "first" });
  log.addEntry(s, { day: "2026-12-20", kind: "decision", text: "second" });
  log.addEntry(s, { day: "2026-12-14", kind: "win", text: "third" });
  assert.deepEqual(log.listEntries(s).map((e) => e.text), ["second", "third", "first"]);
  assert.deepEqual(log.listEntries(s, "win").map((e) => e.text), ["third", "first"]);
  assert.deepEqual(log.counts(s), { all: 3, win: 2, decision: 1, lesson: 0, feedback: 0 });
});

test("removeEntry deletes one entry and ids are never reused", () => {
  const s = store.emptyState();
  log.addEntry(s, { day: "2026-12-14", kind: "win", text: "a" });
  log.addEntry(s, { day: "2026-12-14", kind: "win", text: "b" });
  assert.equal(log.removeEntry(s, "w1"), true);
  assert.equal(log.removeEntry(s, "w1"), false);
  assert.equal(log.addEntry(s, { day: "2026-12-15", kind: "win", text: "c" }).id, "w3");
  assert.deepEqual(log.listEntries(s).map((e) => e.id), ["w3", "w2"]);
});

test("toMarkdown groups by month, newest first, with counts, phases and impact", () => {
  const s = store.emptyState();
  log.addEntry(s, { day: "2026-12-14", kind: "win", text: "Payroll source mapped", impact: "3 reports fed", phase: "P1" });
  log.addEntry(s, { day: "2027-01-12", kind: "feedback", text: "Lead with the answer\nin steering groups" });
  const md = log.toMarkdown(s, "2027-01-20");
  assert.equal(md, [
    "# Work log",
    "",
    "Exported 2027-01-20. 2 entries.",
    "",
    "Win: 1 · Decision: 0 · Lesson learned: 0 · Feedback: 1",
    "",
    "## January 2027",
    "",
    "- **2027-01-12 · Feedback**: Lead with the answer in steering groups",
    "",
    "## December 2026",
    "",
    "- **2026-12-14 · Win (P1)**: Payroll source mapped",
    "  - Impact: 3 reports fed",
    "",
  ].join("\n"));
  assert.ok(log.toMarkdown(store.emptyState(), "2026-12-01").includes("No entries yet."));
});
