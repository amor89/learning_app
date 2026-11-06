// Interview practice views: the hub, the timed theory drill and the timed from-scratch task.
import { needsPython } from "./checkers.js";
import { briefPanel, gradeCode } from "./exercises.js";
import * as iv from "./interview.js";
import { isWarm } from "./pyrunner.js";
import * as store from "./store.js";
import { codeBlock, editor, fill, h, pct, plainCode, progressBar } from "./ui.js";

const TICK_MS = 250;
const LOW_SECONDS = 10;

function notFound(what) {
  return h("section", { class: "page" }, h("h1", {}, "Not found"), h("p", {}, `${what} does not exist.`), h("a", { href: "#/interview" }, "Back to interview practice"));
}

function lessonLinks(lessons, label = "Taught in") {
  return h("div", { class: "taught" },
    h("span", { class: "muted small" }, `${label}: `),
    lessons.map((l, i) => [i ? ", " : "", h("a", { href: `#/lesson/${l.id}` }, `${l.id} ${l.title}`)]),
  );
}

// Calls tick until the node leaves the page, so a view never leaves a timer behind.
function every(node, tick) {
  tick();
  const timer = setInterval(() => {
    if (!node.isConnected) {
      clearInterval(timer);
      return;
    }
    tick();
  }, TICK_MS);
}

// Hub --------------------------------------------------------------------------

export async function interviewView(app) {
  const bank = await app.interview();
  const state = iv.interviewState(app.state);
  const prefs = state.prefs;
  const topicSelect = h("select", { id: "drill-topic", onchange: (e) => { prefs.topic = e.target.value; app.save(); } },
    h("option", { value: "all", selected: prefs.topic === "all" }, `All topics (${bank.questions.length})`),
    bank.topics.map((t) => h("option", { value: t.id, selected: prefs.topic === t.id }, `${t.title} (${t.count})`)),
  );
  const lengthSelect = h("select", { id: "drill-length", onchange: (e) => { prefs.count = Number(e.target.value); app.save(); } },
    iv.DRILL_LENGTHS.map((n) => h("option", { value: n, selected: prefs.count === n }, `${n} questions`)),
  );
  const start = () => {
    app.drill = newDrill(bank, app.state);
    location.hash = "#/interview/drill";
  };
  const recent = [...state.drills].reverse().slice(0, 5);

  return h(
    "section",
    { class: "page interview" },
    h("h1", {}, "Interview practice"),
    h("p", {}, "Timed practice for senior data science interviews: theory questions against the clock, and models you build from scratch. Each item links to the lessons that teach it."),
    app.drill && !app.drill.done
      ? h("a", { class: "card continue", href: "#/interview/drill" }, h("span", { class: "muted small" }, "Drill in progress"), h("strong", {}, `Question ${app.drill.i + 1} of ${app.drill.questions.length}`))
      : null,
    h("h2", {}, "Theory drill"),
    h("p", { class: "muted small" }, "Answer aloud, or jot notes, before the clock runs out. Multiple choice is marked for you. For an open question you see the model answer, then tick the key points you covered. Questions you have not seen, or scored lowest on, come first."),
    h("div", { class: "drill-setup" },
      h("label", { class: "field-label", for: "drill-topic" }, "Topic"), topicSelect,
      h("label", { class: "field-label", for: "drill-length" }, "Length"), lengthSelect,
    ),
    h("div", { class: "actions" }, h("button", { type: "button", class: "btn", onclick: start }, "Start drill")),
    h("ul", { class: "mastery" }, bank.topics.map((t) => {
      const p = iv.topicProgress(bank.questions, state.theory, t.id);
      return h("li", {},
        h("span", { class: "mastery-label" }, `${t.title} · ${p.answered} of ${p.total} answered`),
        progressBar(p.mean ?? 0, `${t.title} average score`),
        h("span", { class: "mastery-value" }, pct(p.mean)),
      );
    })),
    recent.length
      ? h("details", { class: "path-stage drills" },
          h("summary", {}, h("strong", {}, "Recent drills")),
          h("ul", { class: "plain-list" }, recent.map((d) => h("li", {}, h("span", {}, `${d.day} · ${d.topic === "all" ? "All topics" : bank.topics.find((t) => t.id === d.topic)?.title ?? d.topic}`), h("span", { class: "small" }, `${round(d.total)} of ${d.count} · ${pct(d.total / d.count)}`)))),
        )
      : null,
    h("h2", {}, "Build it from scratch"),
    h("p", { class: "muted small" }, "Write a model or metric with NumPy alone, against a time limit. The checker runs hidden tests in your browser. The clock stops when every check passes."),
    h("ol", { class: "module-list" }, bank.tasks.map((task) => {
      const status = iv.taskStatus(state.tasks[task.id], task.minutes * 60_000);
      return h("li", {}, h("a", { class: "card", href: `#/interview/task/${task.id}` },
        h("span", { class: "module-head" }, h("strong", {}, task.title), h("span", { class: `pill${status.ok ? " ok" : ""}` }, status.text)),
        h("span", { class: "muted small" }, `${task.minutes} minutes · ${task.lessons.map((l) => l.id).join(", ")}`),
      ));
    })),
  );
}

function round(x) {
  return Math.round(x * 10) / 10;
}

function newDrill(bank, state) {
  const prefs = iv.interviewState(state).prefs;
  const seed = `${Date.now()}`;
  const questions = iv.pickQuestions(bank.questions, iv.interviewState(state).theory, { ...prefs, seed });
  return { seed, topic: prefs.topic, questions, i: 0, results: [], current: null, done: false };
}

// Drill ------------------------------------------------------------------------

export async function drillView(app) {
  const bank = await app.interview();
  if (!app.drill) app.drill = newDrill(bank, app.state);
  const drill = app.drill;
  const page = h("section", { class: "page interview" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/interview" }, "Interview practice")),
    h("h1", {}, "Theory drill"),
  );
  const box = h("div", {});
  page.append(box);
  const topicTitle = (id) => bank.topics.find((t) => t.id === id)?.title ?? id;

  const finish = () => {
    drill.done = true;
    const score = iv.drillScore(drill.results);
    if (!drill.recorded) {
      drill.recorded = true;
      iv.recordDrill(app.state, { day: store.today(), topic: drill.topic, count: score.count, total: score.total });
      app.save();
    }
    fill(box,
      h("h2", {}, "Drill complete"),
      h("p", { class: "drill-score" }, `${round(score.total)} of ${score.count} · ${pct(score.share)}`),
      h("ol", { class: "drill-results" }, drill.results.map((r) => {
        const q = drill.questions.find((x) => x.id === r.id);
        return h("li", { class: r.score === 1 ? "ok" : "" },
          h("div", { class: "result-head" }, h("span", { class: `pill${r.score === 1 ? " ok" : ""}` }, pct(r.score)), h("span", { class: "muted small" }, `${formatSeconds(r.ms)}${r.timedOut ? " · time ran out" : ""}`)),
          h("div", { class: "result-question", html: q.question_html }),
          r.score < 1 ? lessonLinks(q.lessons, "Review") : null,
        );
      })),
      h("div", { class: "actions" },
        h("button", { type: "button", class: "btn", onclick: () => {
          for (const key of Object.keys(drill)) delete drill[key];
          Object.assign(drill, newDrill(bank, app.state));
          paint();
        } }, "New drill"),
        h("a", { class: "btn secondary", href: "#/interview" }, "Interview home"),
      ),
    );
  };

  const paint = () => {
    if (drill.done || drill.i >= drill.questions.length) return finish();
    const q = drill.questions[drill.i];
    drill.current ??= { id: q.id, deadline: Date.now() + q.seconds * 1000, started: Date.now(), phase: "ask", choice: null, ticks: [], notes: "", timedOut: false };
    const cur = drill.current;
    const clock = h("div", { class: "clock", role: "timer", "aria-live": "off" });
    const bar = h("div", { class: "bar clock-bar" }, h("div", { class: "bar-fill" }));
    const body = h("div", {});
    const after = h("div", { class: "drill-review", hidden: true });
    const actions = h("div", { class: "actions" });

    const review = (timedOut) => {
      if (cur.phase !== "ask") return;
      cur.phase = "review";
      cur.timedOut = timedOut;
      cur.ms = Math.min(Date.now(), cur.deadline) - cur.started;
      store.markActive(app.state);
      app.save();
      paintQuestion();
    };

    const next = () => {
      const score = iv.scoreAnswer(q, { choice: cur.choice, ticks: cur.ticks });
      iv.recordTheory(app.state, q.id, score, store.today());
      drill.results.push({ id: q.id, score, ms: cur.ms, timedOut: cur.timedOut });
      app.save();
      drill.i += 1;
      drill.current = null;
      paint();
      document.querySelector(".drill-head")?.scrollIntoView();
    };

    const paintQuestion = () => {
      const asking = cur.phase === "ask";
      if (q.kind === "mcq") {
        const options = iv.shuffle(q.options, `${q.id}-${drill.seed}`);
        fill(body, h("fieldset", { class: "choices", disabled: !asking },
          h("legend", { class: "sr-only" }, "Options"),
          options.map((o) => h("label", { class: `choice${!asking && o.id === q.answer ? " right" : ""}${!asking && o.id === cur.choice && o.id !== q.answer ? " wrong" : ""}` },
            h("input", { type: "radio", name: `drill-${q.id}`, value: o.id, checked: cur.choice === o.id, onchange: () => (cur.choice = o.id) }),
            h("span", { html: o.html }),
          )),
        ));
      } else {
        const notes = h("textarea", { class: "answer-line", rows: 4, placeholder: "Notes (optional, not marked)", "aria-label": "Your notes", disabled: !asking, oninput: (e) => (cur.notes = e.target.value) });
        notes.value = cur.notes;
        fill(body, h("p", { class: "muted small" }, "Answer aloud as you would in the interview, or jot the key points."), notes);
      }
      if (asking) {
        after.hidden = true;
        fill(actions, h("button", { type: "button", class: "btn", onclick: () => {
          if (q.kind === "mcq" && !cur.choice) return showNote("Pick an option first.");
          review(false);
        } }, q.kind === "mcq" ? "Submit" : "Show model answer"));
        return;
      }
      const correct = q.kind === "mcq" && cur.choice === q.answer;
      fill(after,
        cur.timedOut ? h("p", { class: "feedback bad" }, "Time is up.") : null,
        q.kind === "mcq" ? h("p", { class: `feedback ${correct ? "ok" : "bad"}` }, correct ? "Correct." : cur.choice ? "Not quite." : "No answer given.") : null,
        h("h3", {}, "Model answer"),
        h("div", { class: "explanation", html: q.model_answer_html }),
        q.kind === "open"
          ? h("fieldset", { class: "choices points" }, h("legend", {}, "Tick each point your answer covered"),
              q.points_html.map((html, i) => h("label", { class: "choice" },
                h("input", { type: "checkbox", checked: cur.ticks.includes(i), onchange: (e) => {
                  cur.ticks = e.target.checked ? [...cur.ticks, i] : cur.ticks.filter((x) => x !== i);
                } }),
                h("span", { html }),
              )))
          : null,
        lessonLinks(q.lessons),
      );
      after.hidden = false;
      fill(actions, h("button", { type: "button", class: "btn", onclick: next }, drill.i + 1 < drill.questions.length ? "Next question" : "See results"));
    };

    const showNote = (msg) => {
      fill(after, h("p", { class: "feedback info" }, msg));
      after.hidden = false;
    };

    fill(box,
      h("div", { class: "drill-head" },
        h("span", { class: "muted small" }, `Question ${drill.i + 1} of ${drill.questions.length} · ${topicTitle(q.topic)}`),
        clock,
      ),
      bar,
      h("div", { class: "prompt", html: q.question_html }),
      body,
      after,
      actions,
    );
    paintQuestion();
    every(clock, () => {
      const left = cur.phase === "ask" ? cur.deadline - Date.now() : cur.deadline - cur.started - cur.ms;
      clock.textContent = iv.formatClock(Math.max(0, left));
      clock.classList.toggle("low", cur.phase === "ask" && left <= LOW_SECONDS * 1000);
      bar.firstChild.style.width = `${Math.max(0, Math.min(100, (left / (q.seconds * 1000)) * 100))}%`;
      if (cur.phase === "ask" && left <= 0) review(true);
    });
  };

  paint();
  return page;
}

function formatSeconds(ms) {
  return `${Math.round((ms ?? 0) / 1000)} s`;
}

// From-scratch task ------------------------------------------------------------------

export async function taskView(app, taskId) {
  const bank = await app.interview();
  const task = bank.tasks.find((t) => t.id === taskId);
  if (!task) return notFound(`Task ${taskId}`);
  const limit = task.minutes * 60_000;
  const record = iv.taskRecord(app.state, task.id);
  const workspace = h("div", {});
  const status = h("p", { class: "muted small" });
  const paintStatus = () => {
    const s = iv.taskStatus(record, limit);
    fill(status, `${task.minutes}-minute limit · NumPy only · `, h("span", { class: `pill${s.ok ? " ok" : ""}` }, s.text));
  };
  paintStatus();

  const reminder = task.primer_html
    ? h("details", { class: "reminder", ontoggle: (e) => {
        if (e.target.open && record.run && !record.run.stopped && !record.run.reminder) {
          record.run.reminder = true;
          app.save();
        }
      } },
        h("summary", {}, "Need a reminder of the algorithm?"),
        h("div", { class: "primer", html: task.primer_html }),
      )
    : null;

  const paintWorkspace = () => {
    const run = record.run;
    if (!run) {
      fill(workspace, h("div", { class: "actions" }, h("button", { type: "button", class: "btn", onclick: () => {
        iv.startRun(app.state, task.id, task.starter);
        store.markActive(app.state);
        app.save();
        paintWorkspace();
        paintStatus();
        workspace.querySelector("textarea")?.focus();
      } }, "Start the clock")));
      return;
    }
    const clock = h("div", { class: "clock", role: "timer", "aria-live": "off" });
    const bar = h("div", { class: "bar clock-bar" }, h("div", { class: "bar-fill" }));
    const feedback = h("div", { class: "feedback", role: "status", "aria-live": "polite" });
    const hints = h("ol", { class: "hints" });
    const result = h("div", {});
    const area = editor(run.code, (v) => {
      run.code = v;
      app.save();
    });
    const checkBtn = h("button", { type: "button", class: "btn" }, "Run checks");
    const hintBtn = h("button", { type: "button", class: "btn secondary" });
    const solveBtn = h("button", { type: "button", class: "btn ghost" }, "Show solution");
    const restartBtn = h("button", { type: "button", class: "btn ghost" }, "Start again");

    const paintHints = () => {
      fill(hints, task.hints_html.slice(0, run.hints).map((html, i) => h("li", {}, h("span", { class: "tier" }, `Hint ${i + 1}. `), h("span", { html }))));
      hintBtn.textContent = run.hints >= iv.MAX_HINTS ? "No more hints" : `Hint ${run.hints + 1} of ${iv.MAX_HINTS}`;
      hintBtn.disabled = run.hints >= iv.MAX_HINTS || Boolean(run.stopped);
    };

    const paintResult = () => {
      const finished = Boolean(run.stopped);
      solveBtn.disabled = finished || (record.attempts < 1 && iv.elapsed(run) < limit);
      solveBtn.title = solveBtn.disabled && !finished ? "Make one attempt, or let the clock run out, first" : "";
      area.readOnly = finished;
      checkBtn.disabled = finished;
      if (!finished) {
        fill(result);
        return;
      }
      const ms = run.stopped;
      const verdict = run.passed && !run.solution
        ? `Passed in ${iv.formatClock(ms)}, ${ms <= limit ? `inside the ${task.minutes}-minute limit` : `${iv.formatClock(ms - limit)} over the limit`}.`
        : run.passed
          ? `Passed after you viewed the solution. This run does not count towards your best time.`
          : `You viewed the solution after ${iv.formatClock(ms)}.`;
      fill(result,
        h("p", { class: `feedback ${run.passed && !run.solution ? "ok" : "info"}` }, verdict),
        h("details", { class: "solution-box", open: Boolean(run.solution) },
          h("summary", {}, "Reference solution"),
          codeBlock(task.solution_lines),
          h("div", { class: "explanation", html: task.explanation_html }),
        ),
        h("h2", {}, "Follow-up questions"),
        h("p", { class: "muted small" }, "Interviewers ask these once your code works. Answer aloud first, then open the model answer."),
        h("div", { class: "follow-ups" }, task.follow_ups.map((f) => h("details", { class: "follow-up" },
          h("summary", { html: f.question_html }),
          h("div", { html: f.answer_html }),
        ))),
      );
    };

    checkBtn.addEventListener("click", async () => {
      checkBtn.disabled = true;
      if (needsPython(task.checker)) {
        feedback.className = "feedback info";
        feedback.textContent = isWarm() ? "Running checks…" : "Loading Python and NumPy. The first run downloads about 25 MB and takes a while.";
      }
      try {
        const graded = await gradeCode(task.checker, run.code, task.packages);
        feedback.className = `feedback ${graded.passed ? "ok" : "bad"}`;
        fill(feedback, h("p", {}, graded.feedback));
        if (graded.stdout) feedback.append(h("details", {}, h("summary", {}, "Output"), plainCode(graded.stdout)));
        const outcome = iv.recordCheck(app.state, task.id, graded.passed, limit, store.today());
        store.markActive(app.state);
        app.save();
        if (outcome?.best) app.toast(`New best time: ${iv.formatClock(outcome.ms)}`);
      } catch (error) {
        feedback.className = "feedback bad";
        fill(feedback, h("p", {}, error.message));
      } finally {
        checkBtn.disabled = false;
        paintStatus();
        paintHints();
        paintResult();
      }
    });
    hintBtn.addEventListener("click", () => {
      iv.useHint(run);
      app.save();
      paintHints();
    });
    solveBtn.addEventListener("click", () => {
      iv.revealSolution(run);
      app.save();
      paintHints();
      paintResult();
    });
    restartBtn.addEventListener("click", () => {
      if (!run.stopped && !confirm("Start again? Your code and the clock reset.")) return;
      iv.startRun(app.state, task.id, task.starter);
      app.save();
      paintWorkspace();
      paintStatus();
    });

    fill(workspace,
      h("div", { class: "drill-head" }, h("span", { class: "muted small" }, `Time limit ${task.minutes}:00`), clock),
      bar,
      area,
      h("div", { class: "actions" }, checkBtn, hintBtn, solveBtn, restartBtn),
      feedback,
      hints,
      result,
    );
    paintHints();
    paintResult();
    every(clock, () => {
      const used = iv.elapsed(run);
      const over = used > limit;
      clock.textContent = over ? `+${iv.formatClock(used - limit)}` : iv.formatClock(used);
      clock.classList.toggle("low", over && !run.stopped);
      clock.classList.toggle("stopped", Boolean(run.stopped));
      bar.firstChild.style.width = `${Math.min(100, (used / limit) * 100)}%`;
      bar.classList.toggle("over", over);
      if (!run.stopped && solveBtn.disabled && over) paintResult();
    });
  };
  paintWorkspace();

  return h(
    "article",
    { class: "page interview task" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/interview" }, "Interview practice")),
    h("h1", {}, task.title),
    status,
    lessonLinks(task.lessons),
    h("div", { class: "prompt", html: task.prompt_html }),
    briefPanel(task.brief, null),
    reminder,
    workspace,
  );
}
