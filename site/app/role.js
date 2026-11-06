// Role plan logic: plan dates, your self-assessed levels against the targets, and
// lesson progress per competency. Pure functions, so Node can test them.
import * as store from "./store.js";

const DAY_MS = 86_400_000;

export function roleRecord(state, roleId) {
  state.roles ??= {};
  state.roles[roleId] ??= { levels: {}, assessed: {}, done: {}, phases: {}, assumptions: {} };
  return state.roles[roleId];
}

function toUtc(day) {
  const [y, m, d] = day.split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

// Day 1 is the start date. Before the start the number is 0 or negative.
export function planDay(start, today) {
  return Math.round((toUtc(today) - toUtc(start)) / DAY_MS) + 1;
}

export function dayToDate(start, day) {
  return new Date(toUtc(start) + (day - 1) * DAY_MS).toISOString().slice(0, 10);
}

export function phaseDates(start, phase) {
  return { from: dayToDate(start, phase.days[0]), to: dayToDate(start, phase.days[1]) };
}

// The phase that holds today, the first before the start, or null after the last.
export function currentPhase(role, today) {
  const day = planDay(role.start, today);
  if (day < 1) return role.phases[0];
  return role.phases.find((p) => day >= p.days[0] && day <= p.days[1]) ?? null;
}

export function setLevel(state, roleId, moduleId, level, day) {
  if (![1, 2, 3, 4].includes(level)) throw new Error(`level must be 1 to 4, got ${level}`);
  const record = roleRecord(state, roleId);
  record.levels[moduleId] = level;
  record.assessed[moduleId] = day;
}

export function toggle(state, roleId, kind, key, on) {
  const record = roleRecord(state, roleId);
  if (!(kind in record)) throw new Error(`unknown record ${kind}`);
  if (on) record[kind][key] = true;
  else delete record[kind][key];
}

// Per stream: how many modules you rated, your mean level against the mean target,
// and the modules still below target. Unrated modules count as gaps you have not checked.
export function streamSummary(role, record) {
  return role.streams.map((stream) => {
    const modules = role.modules.filter((m) => m.stream === stream);
    const rated = modules.filter((m) => record.levels[m.id]);
    const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
    return {
      stream,
      modules: modules.length,
      rated: rated.length,
      level: mean(rated.map((m) => record.levels[m.id])),
      target: mean(modules.map((m) => m.target)),
      below: modules.filter((m) => record.levels[m.id] && record.levels[m.id] < m.target).map((m) => m.id),
    };
  });
}

// Lessons of a competency you have completed, using the lesson summaries in the index.
export function lessonProgress(state, lessons, lessonMeta) {
  const done = lessons.filter((l) => {
    const meta = lessonMeta.get(l.id);
    return meta && store.lessonComplete(state, meta);
  }).length;
  return { done, total: lessons.length };
}

export function levelGap(record, module) {
  const level = record.levels[module.id];
  return level ? module.target - level : null;
}
