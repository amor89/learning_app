// Unit tests for search: query words, matching, ranking, highlights and snippets.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import * as s from "../../site/app/search.js";

const index = {
  lessons: [
    { id: "B8-L1", title: "Survey weights and the effective sample size", where: "B8 Statistics", text: "The Kish effective sample size tells you how much precision weights cost." },
    { id: "E2-L3", title: "Governance at the hub, decision rights", where: "E2 DAMA-DMBOK", text: "Data governance decides. Data management does the work." },
    { id: "B1-L1", title: "Sample size", where: "B1 Basics", text: "How many rows you need." },
  ],
  cards: [
    { lesson: "B8-L1", front: "Kish effective sample size", back: "(sum w)^2 / sum(w^2)" },
    { lesson: "E2-L3", front: "Policy, standard, procedure", back: "Policy says what. Standard makes it measurable." },
  ],
  terms: [
    { lesson: "E2-L3", term: "Data governance" },
    { lesson: "E2-L3", term: "decision rights" },
  ],
};
const prepared = s.prepare(index);

test("normalise keeps positions and folds accents", () => {
  assert.equal(s.normalise("Café Résumé"), "cafe resume");
  assert.equal(s.normalise("Café").length, "Café".length);
});

test("queryTerms drops single letters and repeats", () => {
  assert.deepEqual(s.queryTerms("The k-means Means of 2 things"), ["the", "means", "of", "2", "things"]);
  assert.deepEqual(s.queryTerms("  "), []);
});

test("wordStart matches the start of a word only", () => {
  assert.equal(s.wordStart("data governance", "gov"), 5);
  assert.equal(s.wordStart("metadata", "data"), -1);
});

test("every query word must match", () => {
  const result = s.search(prepared, "kish weights");
  assert.deepEqual(result.groups.lessons.map((l) => l.id), ["B8-L1"]);
  assert.equal(s.search(prepared, "kish zebra").total, 0);
});

test("an exact title comes before a longer one", () => {
  assert.deepEqual(s.search(prepared, "sample size").groups.lessons.map((l) => l.id), ["B1-L1", "B8-L1"]);
});

test("results group into terms, lessons and cards", () => {
  const result = s.search(prepared, "governance");
  assert.deepEqual(result.groups.terms.map((t) => t.term), ["Data governance"]);
  assert.deepEqual(result.groups.lessons.map((l) => l.id), ["E2-L3"]);
  assert.deepEqual(result.groups.cards, []);
  assert.equal(s.search(prepared, "standard").groups.cards[0].lesson, "E2-L3");
});

test("highlight marks each match and keeps the original text", () => {
  const parts = s.highlight("Data governance decides. Governance again.", ["governance"]);
  assert.equal(parts.map((p) => p.text).join(""), "Data governance decides. Governance again.");
  assert.deepEqual(parts.filter((p) => p.hit).map((p) => p.text), ["governance", "Governance"]);
});

test("snippet centres on the first match and marks cuts", () => {
  const text = `${"word ".repeat(40)}Kish effective sample size ${"tail ".repeat(60)}`;
  const cut = s.snippet(text, ["kish"], 30);
  assert.ok(cut.startsWith("… ") && cut.endsWith(" …"), cut);
  assert.ok(cut.includes("Kish effective"), cut);
  assert.equal(s.snippet("Short text.", ["short"]), "Short text.");
  const phrase = `size first. ${"pad ".repeat(60)}the effective sample size here ${"end ".repeat(60)}`;
  assert.ok(s.snippet(phrase, ["effective", "sample", "size"], 30).includes("effective sample size"), "the whole phrase wins over an earlier single word");
});

test("words found together rank above the same words scattered", () => {
  const two = s.prepare({
    lessons: [
      { id: "x", title: "Finding the right data", where: "C9", text: "Trust in governance grows slowly." },
      { id: "y", title: "Governance at the hub", where: "E2", text: "Data governance decides." },
    ],
    cards: [],
    terms: [],
  });
  assert.deepEqual(s.search(two, "data governance").groups.lessons.map((l) => l.id), ["y", "x"]);
});

test("the built index finds a lesson by its title and by a term", () => {
  const built = s.prepare(JSON.parse(readFileSync(new URL("../../site/content/search.json", import.meta.url), "utf8")));
  assert.ok(["E2-L1", "E2-L3"].includes(s.search(built, "data governance").groups.lessons[0].id));
  assert.equal(s.search(built, "DAMA wheel").groups.lessons[0].id, "E2-L1");
  assert.ok(s.search(built, "decision rights").groups.terms.some((t) => t.lesson === "E2-L3"));
});
