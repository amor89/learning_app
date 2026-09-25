// Renders one exercise of any type and grades it.
import {
  checkBugLines,
  checkDesign,
  checkFillGap,
  checkMcq,
  checkOrder,
  checkPredict,
  checkText,
  needsPython,
  unseal,
} from "./checkers.js";
import { checkPython, isWarm } from "./pyrunner.js";
import * as store from "./store.js";
import { codeBlock, editor, fill, h, plainCode } from "./ui.js";

const TYPE_LABELS = {
  mcq: "Multiple choice",
  fill_gap: "Fill the gap",
  predict_output: "Predict the output",
  order: "Put in order",
  spot_bug: "Spot the bug",
  write_function: "Write the function",
  refactor: "Refactor",
  design: "Architecture design",
};

// Stable shuffle, so the order puzzle looks the same after a reload.
function seededShuffle(items, seed) {
  let x = [...seed].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  const out = [...items];
  for (let i = out.length - 1; i > 0; i -= 1) {
    x = (x * 1103515245 + 12345) >>> 0;
    const j = x % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

async function gradeCode(checker, code, packages) {
  if (needsPython(checker)) {
    const result = await checkPython(checker, code, packages ?? []);
    return { passed: result.passed, feedback: result.passed ? "All checks passed." : result.feedback, stdout: result.stdout };
  }
  return checkText(checker, code);
}

// Each builder returns { body, answer(), solution(full), check(full, answer) }.
const BUILDERS = {
  mcq(ex, draft) {
    const name = `q-${ex.id}`;
    const radios = (items, html, key) =>
      items.map((o) =>
        h(
          "label",
          { class: "choice" },
          h("input", {
            type: "radio",
            name: `${name}-${key}`,
            value: o.id,
            checked: draft[key] === o.id,
            onchange: () => (draft[key] = o.id),
          }),
          h("span", { html: html[o.id] }),
        ),
      );
    const body = h(
      "div",
      {},
      h("fieldset", { class: "choices" }, h("legend", { class: "sr-only" }, "Options"), radios(ex.options, ex.options_html, "option")),
      ex.reasons.length
        ? h("fieldset", { class: "choices reasons" }, h("legend", {}, "Why?"), radios(ex.reasons, ex.reasons_html, "reason"))
        : null,
    );
    return {
      body,
      answer: () => ({ option: draft.option, reason: draft.reason }),
      check: (full, answer) => checkMcq(full, answer),
      solution: (full) =>
        h(
          "div",
          {},
          h("p", {}, h("strong", {}, "Answer: "), h("span", { html: ex.options_html[full.answer] })),
          full.reason_answer ? h("p", {}, h("strong", {}, "Because: "), h("span", { html: ex.reasons_html[full.reason_answer] })) : null,
        ),
    };
  },

  fill_gap(ex, draft) {
    draft.gaps ??= {};
    const ids = Object.keys(ex.gaps ?? {}).length ? Object.keys(ex.gaps) : [...new Set(ex.template.match(/\[\[(\w+)\]\]/g).map((m) => m.slice(2, -2)))];
    const lines = ex.template_lines.map((line) => {
      const parts = line.split(/(\[\[\w+\]\])/);
      return h(
        "div",
        { class: "ln" },
        h(
          "code",
          {},
          parts.map((part) => {
            const m = part.match(/^\[\[(\w+)\]\]$/);
            if (!m) return part;
            const gap = m[1];
            const width = Math.max(6, (ex.gaps?.[gap]?.accepted[0] ?? "xxxxxxxxxx").length + 2);
            return h("input", {
              class: "gap",
              style: `width:${width}ch`,
              value: draft.gaps[gap] ?? "",
              "aria-label": `Gap ${ids.indexOf(gap) + 1}`,
              autocapitalize: "off",
              autocomplete: "off",
              autocorrect: "off",
              spellcheck: "false",
              oninput: (e) => (draft.gaps[gap] = e.target.value),
            });
          }),
        ),
      );
    });
    return {
      body: h("div", { class: "code fill" }, lines),
      answer: () => draft.gaps,
      check: (full, answer) => checkFillGap(full, answer),
      solution: (full) => {
        const filled = full.template.replace(/\[\[(\w+)\]\]/g, (_, g) => full.gaps[g].accepted[0]);
        return plainCode(filled.trimEnd());
      },
    };
  },

  predict_output(ex, draft) {
    const input = h("textarea", {
      class: "answer-line",
      rows: 2,
      spellcheck: "false",
      autocapitalize: "off",
      autocorrect: "off",
      "aria-label": "Your predicted output",
      placeholder: "Type the exact output",
      oninput: (e) => (draft.text = e.target.value),
    });
    input.value = draft.text ?? "";
    return {
      body: h("div", {}, codeBlock(ex.code_lines), h("label", { class: "field-label" }, "Output", input)),
      answer: () => draft.text,
      check: (full, answer) => checkPredict(full, answer),
      solution: (full) => plainCode(full.answer),
    };
  },

  order(ex, draft) {
    draft.order ??= (() => {
      let shuffled = seededShuffle(ex.items.map((i) => i.id), ex.id);
      if (ex.answer && shuffled.every((id, i) => id === ex.answer[i])) shuffled = [...shuffled].reverse();
      return shuffled;
    })();
    const text = new Map(ex.items.map((i) => [i.id, i.text]));
    const list = h("ol", { class: "order" });
    const move = (index, delta) => {
      const target = index + delta;
      if (target < 0 || target >= draft.order.length) return;
      [draft.order[index], draft.order[target]] = [draft.order[target], draft.order[index]];
      paint();
      list.querySelectorAll("li")[target]?.querySelector(delta < 0 ? ".up" : ".down")?.focus();
    };
    const paint = () =>
      fill(list, 
        ...draft.order.map((id, i) =>
          h(
            "li",
            {},
            h("span", { class: "order-text" }, text.get(id)),
            h("span", { class: "order-buttons" },
              h("button", { type: "button", class: "icon up", "aria-label": `Move "${text.get(id)}" up`, disabled: i === 0, onclick: () => move(i, -1) }, "↑"),
              h("button", { type: "button", class: "icon down", "aria-label": `Move "${text.get(id)}" down`, disabled: i === draft.order.length - 1, onclick: () => move(i, 1) }, "↓"),
            ),
          ),
        ),
      );
    paint();
    return {
      body: list,
      answer: () => draft.order,
      check: (full, answer) => checkOrder(full, answer),
      solution: (full) => h("ol", {}, full.answer.map((id) => h("li", {}, text.get(id)))),
    };
  },

  design(ex, draft) {
    draft.picks ??= {};
    const body = h(
      "div",
      { class: "design" },
      ex.slots.map((slot) => {
        const select = h(
          "select",
          { "aria-label": slot.label, onchange: (e) => (draft.picks[slot.id] = e.target.value) },
          h("option", { value: "" }, "Choose…"),
          slot.options.map((o) => h("option", { value: o.id, selected: draft.picks[slot.id] === o.id }, o.text)),
        );
        return h("label", { class: "slot" }, h("span", {}, slot.label), select);
      }),
    );
    return {
      body,
      answer: () => draft.picks,
      check: (full, answer) => checkDesign(full, answer),
      solution: (full) => h("div", { html: full.model_answer_html }),
    };
  },
};

function codeBuilder(ex, draft) {
  draft.code ??= ex.starter ?? "";
  return {
    body: editor(draft.code, (v) => (draft.code = v)),
    answer: () => draft.code,
    check: (full, answer) => gradeCode(full.checker, answer, ex.packages),
    solution: (full) => codeBlock(full.solution_lines),
  };
}
BUILDERS.write_function = codeBuilder;
BUILDERS.refactor = codeBuilder;

function spotBugBuilder(ex, draft, frame) {
  draft.lines ??= [];
  draft.fix ??= ex.code;
  draft.linesOk ??= false;
  const holder = h("div", {});
  const paint = () => {
    fill(holder, 
      h("p", { class: "muted small" }, "Tap a line to mark it. Tap again to clear it."),
      codeBlock(ex.code_lines, {
        selected: draft.lines,
        className: "tappable",
        onLine: (n) => {
          if (draft.linesOk) return;
          draft.lines = draft.lines.includes(n) ? draft.lines.filter((x) => x !== n) : [...draft.lines, n];
          paint();
        },
      }),
      draft.linesOk && ex.fix_checker
        ? h("div", { class: "fix" }, h("p", {}, h("strong", {}, "Now fix the code.")), editor(draft.fix, (v) => (draft.fix = v), "Fix editor"))
        : null,
    );
  };
  paint();
  return {
    body: holder,
    answer: () => ({ lines: draft.lines, fix: draft.fix }),
    check: async (full, answer) => {
      if (!draft.linesOk) {
        const result = checkBugLines(full, answer.lines);
        if (!result.passed) return result;
        draft.linesOk = true;
        paint();
        if (!ex.fix_checker) return result;
        frame.announce("You found the bug. Now fix the code and check again.");
        return { passed: false, feedback: "You found the bug. Now fix the code and check again.", partial: true };
      }
      return gradeCode(ex.fix_checker, answer.fix, ex.packages);
    },
    solution: (full) =>
      h(
        "div",
        {},
        codeBlock(ex.code_lines, { flagged: full.bug_lines }),
        full.fix_solution_lines ? h("div", {}, h("p", {}, h("strong", {}, "Fixed version")), codeBlock(full.fix_solution_lines)) : null,
      ),
  };
}
BUILDERS.spot_bug = spotBugBuilder;

export function renderExercise(app, ex, position, total, onChange) {
  const draft = (app.drafts[ex.id] ??= {});
  const status = () => app.state.ex[ex.id] ?? { attempts: 0, hints: 0, passed: null, solution: false };
  const feedback = h("div", { class: "feedback", role: "status", "aria-live": "polite" });
  const hints = h("ol", { class: "hints" });
  const solutionBox = h("div", { class: "solution", hidden: true });
  const frame = { announce: (msg) => (feedback.textContent = msg) };
  const builder = BUILDERS[ex.type](ex, draft, frame);

  const checkBtn = h("button", { type: "button", class: "btn" }, ex.type.match(/write|refactor/) ? "Run checks" : "Check");
  const hintBtn = h("button", { type: "button", class: "btn secondary" }, "Hint");
  const solveBtn = h("button", { type: "button", class: "btn ghost" }, "Show solution");

  const paintHints = () => {
    const shown = status().hints;
    fill(hints, ...ex.hints_html.slice(0, shown).map((html, i) => h("li", {}, h("span", { class: "tier" }, `Hint ${i + 1}. `), h("span", { html }))));
    hintBtn.textContent = shown >= 3 ? "No more hints" : `Hint ${shown + 1} of 3`;
    hintBtn.disabled = shown >= 3;
  };

  const showSolution = () => {
    const full = unseal(ex);
    fill(solutionBox, h("h4", {}, "Solution"), builder.solution(full), h("div", { class: "explanation", html: full.explanation_html }));
    solutionBox.hidden = false;
  };

  const paintButtons = () => {
    const s = status();
    solveBtn.disabled = s.attempts < 1;
    solveBtn.title = s.attempts < 1 ? "Make one attempt first" : "";
    if (s.passed || s.solution) showSolution();
  };

  const setFeedback = (result) => {
    feedback.className = `feedback ${result.passed ? "ok" : result.partial ? "info" : "bad"}`;
    fill(feedback, h("p", {}, result.feedback));
    if (result.stdout) feedback.append(h("details", {}, h("summary", {}, "Output"), plainCode(result.stdout)));
  };

  checkBtn.addEventListener("click", async () => {
    checkBtn.disabled = true;
    const python = needsPython(ex.checker) || (ex.type === "spot_bug" && draft.linesOk && needsPython(ex.fix_checker));
    if (python) {
      feedback.className = "feedback info";
      feedback.textContent = isWarm() ? "Running checks…" : "Loading Python. The first run downloads about 15 MB and takes a while.";
    }
    try {
      const result = await builder.check(unseal(ex), builder.answer());
      setFeedback(result);
      if (!result.partial) {
        const earned = store.recordAttempt(app.state, ex.id, result.passed, ex.xp);
        app.save();
        if (earned) app.toast(`+${earned} XP`);
        onChange();
      }
    } catch (error) {
      setFeedback({ passed: false, feedback: error.message });
    } finally {
      checkBtn.disabled = false;
      paintButtons();
    }
  });

  hintBtn.addEventListener("click", () => {
    store.recordHint(app.state, ex.id);
    app.save();
    paintHints();
  });

  solveBtn.addEventListener("click", () => {
    store.recordSolutionSeen(app.state, ex.id);
    app.save();
    showSolution();
    onChange();
  });

  paintHints();
  paintButtons();
  const s = status();
  const badge = s.passed ? h("span", { class: "pill ok" }, "Passed") : s.solution ? h("span", { class: "pill" }, "Solution seen") : null;

  return h(
    "article",
    { class: "exercise", "aria-labelledby": `ex-${ex.id}` },
    h("header", { class: "exercise-head" },
      h("h3", { id: `ex-${ex.id}` }, `Exercise ${position} of ${total}`),
      h("p", { class: "muted small" }, `${TYPE_LABELS[ex.type]} · Level ${ex.difficulty} · ${ex.xp} XP`, " ", badge),
    ),
    h("div", { class: "prompt", html: ex.prompt_html }),
    builder.body,
    h("div", { class: "actions" }, checkBtn, hintBtn, solveBtn),
    feedback,
    hints,
    solutionBox,
  );
}
