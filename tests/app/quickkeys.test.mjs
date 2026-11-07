// Unit tests for the quick keys above the on-screen keyboard.
import assert from "node:assert/strict";
import { test } from "node:test";

import { applyKey, KEYS, wantsQuickKeys } from "../../site/app/quickkeys.js";

// Text with | marking the cursor, or [ and ] marking a selection.
function parse(marked) {
  const start = marked.search(/[|[]/);
  if (marked[start] === "|") return { text: marked.replace("|", ""), start, end: start };
  const text = marked.replace("[", "").replace("]", "");
  return { text, start, end: marked.indexOf("]") - 1 };
}

function show({ text, start, end }) {
  return start === end ? `${text.slice(0, start)}|${text.slice(start)}` : `${text.slice(0, start)}[${text.slice(start, end)}]${text.slice(end)}`;
}

function press(marked, key) {
  const { text, start, end } = parse(marked);
  return show(applyKey(text, start, end, key));
}

test("a plain key replaces the selection and moves the cursor after it", () => {
  assert.equal(press("x|", ":"), "x:|");
  assert.equal(press("a [bc] d", "_"), "a _| d");
});

test("brackets and quotes insert a pair with the cursor inside", () => {
  assert.equal(press("print|", "("), "print(|)");
  assert.equal(press("x = |", '"'), 'x = "|"');
});

test("brackets wrap a selection and keep it selected", () => {
  assert.equal(press("len [items] + 1", "("), "len ([items]) + 1");
  assert.equal(press("[name]", "'"), "'[name]'");
});

test("tab inserts four spaces at the cursor", () => {
  assert.equal(press("def f():\n|", "tab"), "def f():\n    |");
});

test("tab indents every line of a selection", () => {
  assert.equal(press("[a = 1\nb = 2]", "tab"), "    [a = 1\n    b = 2]");
});

test("dedent removes up to four spaces from the current line", () => {
  assert.equal(press("        x = 1|", "dedent"), "    x = 1|");
  assert.equal(press("  y|", "dedent"), "y|");
  assert.equal(press("z|", "dedent"), "z|");
});

test("dedent never moves the cursor before the line start", () => {
  assert.equal(press("a\n  |  b", "dedent"), "a\n|b");
});

test("dedent works on every selected line", () => {
  assert.equal(press("    [a\n    b]", "dedent"), "[a\nb]");
});

test("the row has the keys Python needs most", () => {
  const keys = KEYS.map(([, key]) => key);
  for (const key of ["tab", "dedent", "(", "[", "{", ":", '"', "'", "=", "_", "#"]) assert.ok(keys.includes(key), key);
});

test("quick keys show only on a coarse pointer", () => {
  assert.equal(wantsQuickKeys({ matchMedia: () => ({ matches: true }) }), true);
  assert.equal(wantsQuickKeys({ matchMedia: () => ({ matches: false }) }), false);
  assert.equal(wantsQuickKeys({}), false);
});
