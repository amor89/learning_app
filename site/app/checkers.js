// Checkers for exercise types graded in the browser without Python.
// Pure functions: the app and the Node test suite import this file.
// Every checker returns { passed, feedback, ruleId }.

const GENERIC = "Not quite. Try a hint, or look again at the prompt.";

export function collapse(text) {
  return String(text ?? "")
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter((line) => line.length > 0)
    .join("\n");
}

function sameSet(a, b) {
  const x = [...new Set(a)].sort();
  const y = [...new Set(b)].sort();
  return x.length === y.length && x.every((v, i) => v === y[i]);
}

function pass(feedback = "Correct.") {
  return { passed: true, feedback, ruleId: "" };
}

function fail(feedback, ruleId = "") {
  return { passed: false, feedback, ruleId };
}

// Multiple choice ------------------------------------------------------------

export function checkMcq(ex, answer) {
  const option = answer?.option;
  const reason = answer?.reason;
  const lookup = (key) => ex.wrong_answers.find((w) => w.answer === key)?.feedback;
  if (!option) return fail("Pick an option first.");
  if (ex.reasons.length && !reason) return fail("Pick a reason as well.");
  if (option !== ex.answer) return fail(lookup(option) ?? GENERIC);
  if (ex.reasons.length && reason !== ex.reason_answer) {
    return fail(lookup(`${option}|${reason}`) ?? "Right answer. Check your reasoning.");
  }
  return pass();
}

// Fill the gap ---------------------------------------------------------------

function gapMatches(gap, value) {
  const norm = (s) => {
    const t = String(s ?? "").replace(/\s+/g, " ").trim();
    return gap.case_sensitive ? t : t.toLowerCase();
  };
  return gap.accepted.some((a) => norm(a) === norm(value));
}

export function checkFillGap(ex, answer) {
  const values = answer ?? {};
  const norm = (s) => String(s ?? "").replace(/\s+/g, " ").trim();
  for (const wrong of ex.wrong_answers) {
    const hit = Object.entries(wrong.answer).every(([g, v]) => norm(values[g]) === norm(v));
    if (hit) return fail(wrong.feedback);
  }
  const ids = Object.keys(ex.gaps);
  const bad = ids.filter((g) => !gapMatches(ex.gaps[g], values[g]));
  if (bad.length === 0) return pass();
  const numbers = bad.map((g) => ids.indexOf(g) + 1).join(", ");
  return fail(`Gap ${numbers} ${bad.length > 1 ? "are" : "is"} not right yet.`);
}

// Predict the output --------------------------------------------------------

export function normaliseOutput(text) {
  return collapse(text).replace(/"/g, "'");
}

export function checkPredict(ex, answer) {
  const given = normaliseOutput(answer);
  if (!given) return fail("Type the output first.");
  const accepted = [ex.answer, ...ex.accepted].map(normaliseOutput);
  if (accepted.includes(given)) return pass();
  const wrong = ex.wrong_answers.find((w) => normaliseOutput(w.answer) === given);
  return fail(wrong?.feedback ?? GENERIC);
}

// Ordering ------------------------------------------------------------------

export function checkOrder(ex, answer) {
  const order = answer ?? [];
  if (order.length === ex.answer.length && order.every((id, i) => id === ex.answer[i])) {
    return pass();
  }
  const wrong = ex.wrong_answers.find(
    (w) => w.answer.length === order.length && w.answer.every((id, i) => id === order[i]),
  );
  if (wrong) return fail(wrong.feedback);
  const first = order.findIndex((id, i) => id !== ex.answer[i]);
  return fail(`Step ${first + 1} is out of place.`);
}

// Spot the bug: line selection ----------------------------------------------

export function checkBugLines(ex, lines) {
  const picked = lines ?? [];
  if (picked.length === 0) return fail("Tap the line with the bug.");
  if (sameSet(picked, ex.bug_lines)) return pass("You found the bug.");
  const wrong = ex.wrong_answers.find((w) => sameSet(w.lines, picked));
  if (wrong) return fail(wrong.feedback);
  const found = ex.bug_lines.every((n) => picked.includes(n));
  if (found) return fail("You found the bug, but you also marked lines that are fine.");
  return fail(GENERIC);
}

// Architecture design --------------------------------------------------------

export function checkDesign(ex, answer) {
  const picks = answer ?? {};
  const missing = ex.slots.filter((s) => !picks[s.id]);
  if (missing.length) return fail("Choose an option for every workload.");
  if (ex.slots.every((s) => picks[s.id] === s.answer)) return pass();
  for (const wrong of ex.wrong_answers) {
    if (Object.entries(wrong.answer).every(([slot, opt]) => picks[slot] === opt)) {
      return fail(wrong.feedback);
    }
  }
  const slot = ex.slots.find((s) => picks[s.id] !== s.answer);
  return fail(`Rethink: ${slot.label}`);
}

// Text rules for SQL, T-SQL, KQL and DAX ------------------------------------

const COMMENT_PATTERNS = {
  sql: [/--[^\n]*/g, /\/\*[\s\S]*?\*\//g],
  dax: [/\/\/[^\n]*/g, /--[^\n]*/g, /\/\*[\s\S]*?\*\//g],
  kql: [/\/\/[^\n]*/g],
  none: [],
};

export function stripComments(code, style) {
  return (COMMENT_PATTERNS[style] ?? []).reduce((text, re) => text.replace(re, " "), code);
}

export function checkText(checker, code) {
  const text = stripComments(String(code ?? ""), checker.comments).replace(/\s+/g, " ").trim();
  if (!text) return fail("Write your answer first.", "empty");
  for (const rule of checker.rules) {
    const found = new RegExp(rule.pattern, "i").test(text);
    const ok = rule.type === "required" ? found : !found;
    if (!ok) return fail(rule.message, rule.id);
  }
  return pass();
}

// Sealed answer keys (Track D7) ------------------------------------------------

export function unseal(ex) {
  if (!ex.sealed) return ex;
  const bytes = Uint8Array.from(atob(ex.sealed), (c) => c.charCodeAt(0));
  const secret = JSON.parse(new TextDecoder().decode(bytes));
  const { sealed, ...rest } = ex;
  return { ...rest, ...secret };
}

// Dispatcher for everything that does not need Python -------------------------

export function checkLocal(ex, answer) {
  const full = unseal(ex);
  switch (full.type) {
    case "mcq":
      return checkMcq(full, answer);
    case "fill_gap":
      return checkFillGap(full, answer);
    case "predict_output":
      return checkPredict(full, answer);
    case "order":
      return checkOrder(full, answer);
    case "design":
      return checkDesign(full, answer);
    default:
      throw new Error(`checkLocal does not handle ${full.type}`);
  }
}

export function needsPython(checker) {
  return checker?.kind === "python";
}
