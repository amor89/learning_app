// Interview practice logic: which questions to ask, how answers score, and the task clock.
// Pure functions over the interview bank and the progress state, so Node can test them.

export const DRILL_LENGTHS = [5, 10, 20];
export const MAX_DRILLS_KEPT = 20;
export const MAX_HINTS = 3;

export function interviewState(state) {
  state.interview ??= {};
  state.interview.theory ??= {};
  state.interview.tasks ??= {};
  state.interview.drills ??= [];
  state.interview.prefs ??= { topic: "all", count: 10 };
  return state.interview;
}

// Stable shuffle from a string seed, so a drill keeps its option order after a reload.
export function shuffle(items, seed) {
  let x = [...String(seed)].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  const out = [...items];
  for (let i = out.length - 1; i > 0; i -= 1) {
    x = (x * 1103515245 + 12345) >>> 0;
    const j = x % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// Theory drill -----------------------------------------------------------------

// Weakest first: questions never asked, then the lowest last score, then the longest unseen.
// The seed breaks ties, so two drills on the same day differ.
export function pickQuestions(questions, theory, { topic = "all", count = 10, seed = "" } = {}) {
  const pool = questions.filter((q) => topic === "all" || q.topic === topic);
  const order = new Map(shuffle(pool.map((q) => q.id), seed).map((id, i) => [id, i]));
  const key = (q) => {
    const r = theory[q.id];
    return r ? [1, r.last, r.day] : [0, 0, ""];
  };
  return [...pool]
    .sort((a, b) => {
      const [ka, kb] = [key(a), key(b)];
      for (let i = 0; i < ka.length; i += 1) {
        if (ka[i] < kb[i]) return -1;
        if (ka[i] > kb[i]) return 1;
      }
      return order.get(a.id) - order.get(b.id);
    })
    .slice(0, count);
}

// 1 or 0 for multiple choice, the share of key points covered for an open question.
export function scoreAnswer(question, answer) {
  if (question.kind === "mcq") return answer?.choice === question.answer ? 1 : 0;
  const ticked = new Set(answer?.ticks ?? []);
  const total = question.points_html.length;
  return total ? [...ticked].filter((i) => i >= 0 && i < total).length / total : 0;
}

export function recordTheory(state, questionId, score, day) {
  const theory = interviewState(state).theory;
  const r = theory[questionId] ?? { seen: 0, last: 0, best: 0, day: null };
  theory[questionId] = { seen: r.seen + 1, last: score, best: Math.max(r.best, score), day };
  return theory[questionId];
}

export function recordDrill(state, drill) {
  const drills = interviewState(state).drills;
  drills.push(drill);
  drills.splice(0, Math.max(0, drills.length - MAX_DRILLS_KEPT));
}

export function drillScore(results) {
  const total = results.reduce((sum, r) => sum + r.score, 0);
  return { total, count: results.length, share: results.length ? total / results.length : 0 };
}

// Answered questions in a topic and their mean last score (null before the first answer).
export function topicProgress(questions, theory, topic) {
  const ids = questions.filter((q) => topic === "all" || q.topic === topic).map((q) => q.id);
  const seen = ids.filter((id) => theory[id]);
  const mean = seen.length ? seen.reduce((s, id) => s + theory[id].last, 0) / seen.length : null;
  return { answered: seen.length, total: ids.length, mean };
}

// Clock ------------------------------------------------------------------------

// 0:07, 1:30, 25:00. Negative times show the overrun with a minus sign.
export function formatClock(ms) {
  const sign = ms < 0 ? "-" : "";
  const seconds = Math.floor(Math.abs(ms) / 1000);
  return `${sign}${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

// From-scratch tasks ---------------------------------------------------------------

export function taskRecord(state, taskId) {
  const tasks = interviewState(state).tasks;
  tasks[taskId] ??= { attempts: 0, passes: 0, best: null, run: null };
  return tasks[taskId];
}

export function startRun(state, taskId, starter, now = Date.now()) {
  const record = taskRecord(state, taskId);
  record.run = { start: now, code: starter, hints: 0, reminder: false, solution: false, stopped: null, passed: false };
  return record.run;
}

export function elapsed(run, now = Date.now()) {
  if (!run) return 0;
  return run.stopped ?? Math.max(0, now - run.start);
}

export function useHint(run) {
  run.hints = Math.min(MAX_HINTS, run.hints + 1);
  return run.hints;
}

export function revealSolution(run, now = Date.now()) {
  run.solution = true;
  run.stopped ??= Math.max(0, now - run.start);
}

// Records one check. A first pass stops the clock. It counts towards the best time only
// when the solution stayed hidden.
export function recordCheck(state, taskId, passed, limitMs, day, now = Date.now()) {
  const record = taskRecord(state, taskId);
  const run = record.run;
  record.attempts += 1;
  if (!run || !passed || run.passed) return null;
  run.passed = true;
  run.stopped ??= Math.max(0, now - run.start);
  const clean = !run.solution;
  const result = { ms: run.stopped, over: run.stopped > limitMs, clean, best: false };
  if (clean) {
    record.passes += 1;
    if (!record.best || run.stopped < record.best.ms) {
      record.best = { ms: run.stopped, day, hints: run.hints, reminder: run.reminder, over: result.over };
      result.best = true;
    }
  }
  return result;
}

// One line for the task list: never tried, in progress, or the best clean time.
export function taskStatus(record, limitMs) {
  if (record?.best) {
    const extras = [record.best.hints ? `${record.best.hints} hint${record.best.hints > 1 ? "s" : ""}` : "", record.best.reminder ? "reminder" : ""].filter(Boolean);
    const over = record.best.ms > limitMs ? ", over time" : "";
    return { text: `Best ${formatClock(record.best.ms)}${over}${extras.length ? ` (${extras.join(", ")})` : ""}`, ok: record.best.ms <= limitMs };
  }
  if (record?.run && !record.run.stopped) return { text: "Clock running", ok: false };
  if (record?.attempts) return { text: "Not passed yet", ok: false };
  return { text: "Not tried", ok: false };
}
