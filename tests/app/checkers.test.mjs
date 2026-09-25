// Quality gates for exercises graded in JavaScript.
// Run after `python scripts/build_content.py`: node --test tests/app/
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";

import {
  checkBugLines,
  checkLocal,
  checkText,
  unseal,
} from "../../site/app/checkers.js";

const fixture = JSON.parse(
  readFileSync(new URL("./exercises.generated.json", import.meta.url), "utf8"),
);
const LOCAL = new Set(["mcq", "fill_gap", "predict_output", "order", "design"]);

function solutionOf(ex) {
  switch (ex.type) {
    case "mcq":
      return { option: ex.answer, reason: ex.reason_answer ?? undefined };
    case "fill_gap":
      return Object.fromEntries(Object.entries(ex.gaps).map(([g, v]) => [g, v.accepted[0]]));
    case "predict_output":
      return ex.answer;
    case "order":
      return ex.answer;
    case "design":
      return Object.fromEntries(ex.slots.map((s) => [s.id, s.answer]));
    default:
      throw new Error(ex.type);
  }
}

function wrongOf(ex, wrong) {
  switch (ex.type) {
    case "mcq": {
      const [option, reason] = wrong.answer.split("|");
      return { option, reason: reason ?? (ex.reasons.length ? ex.reason_answer : undefined) };
    }
    case "fill_gap":
      return { ...solutionOf(ex), ...wrong.answer };
    case "design":
      return { ...solutionOf(ex), ...wrong.answer };
    default:
      return wrong.answer;
  }
}

for (const ex of fixture.filter((e) => LOCAL.has(e.type))) {
  test(`${ex.id} solution passes`, () => {
    assert.equal(checkLocal(ex, solutionOf(ex)).passed, true);
  });
  ex.wrong_answers.forEach((wrong, i) => {
    test(`${ex.id} wrong answer ${i} gives its feedback`, () => {
      const result = checkLocal(ex, wrongOf(ex, wrong));
      assert.equal(result.passed, false);
      assert.equal(result.feedback, wrong.feedback);
    });
  });
}

for (const ex of fixture.filter((e) => e.type === "spot_bug")) {
  test(`${ex.id} bug lines pass`, () => {
    assert.equal(checkBugLines(ex, ex.bug_lines).passed, true);
  });
  ex.wrong_answers.forEach((wrong, i) => {
    test(`${ex.id} wrong lines ${i} give their feedback`, () => {
      const result = checkBugLines(ex, wrong.lines);
      assert.equal(result.passed, false);
      assert.equal(result.feedback, wrong.feedback);
    });
  });
  if (ex.fix_checker?.kind === "text") {
    test(`${ex.id} text fix passes and the buggy code fails`, () => {
      assert.equal(checkText(ex.fix_checker, ex.fix_solution).passed, true);
      for (const code of [ex.code, ...ex.fix_seeded_bugs]) {
        assert.equal(checkText(ex.fix_checker, code).passed, false);
      }
    });
  }
}

for (const ex of fixture.filter((e) => e.checker?.kind === "text")) {
  test(`${ex.id} text solution passes, starter and seeded bugs fail`, () => {
    assert.equal(checkText(ex.checker, ex.solution).passed, true);
    if (ex.starter) assert.equal(checkText(ex.checker, ex.starter).passed, false);
    for (const bug of ex.seeded_bugs) assert.equal(checkText(ex.checker, bug).passed, false);
  });
  ex.wrong_answers.forEach((wrong, i) => {
    test(`${ex.id} text wrong answer ${i} triggers ${wrong.triggers}`, () => {
      assert.equal(checkText(ex.checker, wrong.answer).ruleId, wrong.triggers);
    });
  });
}

test("every built lesson file parses and matches the fixture", () => {
  const dir = new URL("../../site/content/lessons/", import.meta.url);
  const ids = new Set(fixture.map((e) => e.id));
  let count = 0;
  for (const name of readdirSync(dir)) {
    const lesson = JSON.parse(readFileSync(new URL(name, dir), "utf8"));
    for (const ex of lesson.exercises) {
      assert.ok(ids.has(ex.id), ex.id);
      assert.equal(ex.seeded_bugs, undefined, "seeded bugs must not ship to the app");
      count += 1;
    }
  }
  assert.equal(count, fixture.length);
});

test("unseal restores a hidden key", () => {
  const secret = { answer: "b" };
  const sealed = Buffer.from(JSON.stringify(secret)).toString("base64");
  assert.deepEqual(unseal({ id: "x", sealed }), { id: "x", answer: "b" });
});
