// Unit tests for monthly notes: saving, word counts, Markdown from the quick reference, and export.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import * as notes from "../../site/app/notes.js";
import * as store from "../../site/app/store.js";

const sheet = {
  id: "B23",
  title: "PyTorch foundations",
  lessons: [{
    id: "B23-L1",
    title: "Tensors",
    takeaway_html: "Convert to <code>float32</code> at the edge &amp; check shapes.",
    recap: [{ front_html: "Default floats", back_html: "PyTorch <code>float32</code>, NumPy <em>float64</em>." }],
  }],
};

test("notes save per month with the day they changed, and old exports gain an empty record", () => {
  const s = store.emptyState();
  assert.deepEqual(notes.noteFor(s, "m1-3"), { quick: "", deep: "", updated: null });
  notes.setNote(s, "m1-3", "quick", "Tensors are typed", "2026-11-06");
  assert.deepEqual(s.notes["m1-3"], { quick: "Tensors are typed", deep: "", updated: "2026-11-06" });
  assert.throws(() => notes.setNote(s, "m1-3", "title", "x", "d"));
  const { notes: dropped, ...old } = store.emptyState();
  assert.deepEqual(store.migrate(old).notes, {});
});

test("wordCount counts words, numbers and code-ish tokens", () => {
  assert.equal(notes.wordCount(""), 0);
  assert.equal(notes.wordCount(undefined), 0);
  assert.equal(notes.wordCount("Adam's lr is 1e-3, not 0.1."), 6);
});

test("htmlToMarkdown keeps code and emphasis, and decodes entities", () => {
  assert.equal(notes.htmlToMarkdown("Use <code>x &lt; 1</code> &amp; <strong>check</strong> <em>it</em>"), "Use `x < 1` & **check** *it*");
  assert.equal(notes.htmlToMarkdown('<a href="#/lesson/B1">B1</a>'), "B1");
});

test("quickrefMarkdown lists each lesson's takeaway and recap facts", () => {
  assert.equal(notes.quickrefMarkdown([sheet]), [
    "### B23 PyTorch foundations",
    "",
    "- **B23-L1 Tensors**: Convert to `float32` at the edge & check shapes.",
    "  - Default floats: PyTorch `float32`, NumPy *float64*.",
    "",
  ].join("\n"));
});

test("exportMarkdown writes one file with both sections, marking empty ones", () => {
  const month = { title: "Months 1 to 3: PyTorch foundations", summary: "Tensors and training." };
  const md = notes.exportMarkdown(month, { quick: "My facts", deep: "", updated: "2026-11-05" }, sheet.lessons, "2026-11-06");
  assert.ok(md.startsWith("# Months 1 to 3: PyTorch foundations\n"));
  assert.ok(md.includes("Exported 2026-11-06, last edited 2026-11-05."));
  assert.ok(md.includes("- B23-L1 Tensors\n"));
  assert.ok(md.includes("## Quick reference\n\nMy facts\n"));
  assert.ok(md.includes("## Deep dive\n\n_Not written yet._\n"));
});

test("noteStatus summarises a month's notes", () => {
  assert.equal(notes.noteStatus(undefined), "No notes yet");
  assert.equal(notes.noteStatus({ quick: " ", deep: "", updated: "d" }), "No notes yet");
  assert.equal(notes.noteStatus({ quick: "one two", deep: "three", updated: "2026-11-06" }), "Quick reference 2 words · deep dive 1 words · edited 2026-11-06");
});

test("the built index lists the roadmap months with a quick-reference PDF each", () => {
  const index = JSON.parse(readFileSync(new URL("../../site/content/index.json", import.meta.url), "utf8"));
  const pathway = index.pathways.find((p) => p.id === index.months.pathway);
  assert.ok(pathway);
  for (const month of index.months.stages) {
    assert.ok(pathway.stages.some((s) => s.id === month.id), month.id);
    assert.ok(month.quickref?.endsWith(`quickref-${month.id}.pdf`), month.id);
    assert.ok(month.modules.length > 0, month.id);
  }
});
