// Unit tests for the header's Back logic.
import assert from "node:assert/strict";
import { test } from "node:test";

import { backTarget, isRoot, visit } from "../../site/app/nav.js";

test("tab pages are roots and other pages are not", () => {
  for (const hash of ["", "#/", "#/paths", "#/interview", "#/review", "#/settings"]) assert.ok(isRoot(hash), hash);
  for (const hash of ["#/lesson/B1-L1", "#/module/B1", "#/library", "#/interview/drill", "#/path/ds-roadmap"]) assert.ok(!isRoot(hash), hash);
});

test("visits push, and returning to the previous page pops", () => {
  let stack = visit([], "#/");
  stack = visit(stack, "#/module/B1");
  stack = visit(stack, "#/lesson/B1-L1");
  assert.deepEqual(stack, ["#/", "#/module/B1", "#/lesson/B1-L1"]);
  stack = visit(stack, "#/module/B1");
  assert.deepEqual(stack, ["#/", "#/module/B1"]);
  assert.deepEqual(visit(stack, "#/module/B1"), stack, "a re-render of the same page changes nothing");
});

test("Back uses history when there is some, otherwise the parent page", () => {
  assert.equal(backTarget(["#/", "#/lesson/B1-L1"], "#/module/B1"), "history");
  assert.equal(backTarget(["#/lesson/B1-L1"], "#/module/B1"), "#/module/B1");
  assert.equal(backTarget(["#/lesson/B1-L1"], null), "#/");
});
