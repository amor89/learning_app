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

// Countdown --------------------------------------------------------------------
// Your own settings for the countdown on the role page and Home: your start date
// (it also dates the phases), the phases whose lessons you want done, the deadline
// (your start date or the end of a phase) and the days a week you study.

export const COUNTDOWN_DEFAULTS = { through: "P2", by: "start", per_week: 5, home: true };

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

function validDay(day) {
  if (typeof day !== "string" || !ISO_DAY.test(day)) return false;
  return new Date(toUtc(day)).toISOString().slice(0, 10) === day;
}

// Saved settings over the defaults. A value that no longer fits the plan falls back.
export function countdownSettings(plan, record) {
  const saved = record?.countdown ?? {};
  const ids = plan.phases.map((p) => p.id);
  return {
    start: validDay(saved.start) ? saved.start : plan.start,
    through: ids.includes(saved.through) ? saved.through : ids.includes(COUNTDOWN_DEFAULTS.through) ? COUNTDOWN_DEFAULTS.through : ids[0],
    by: saved.by === "start" || ids.includes(saved.by) ? saved.by : COUNTDOWN_DEFAULTS.by,
    per_week: Number.isInteger(saved.per_week) && saved.per_week >= 1 && saved.per_week <= 7 ? saved.per_week : COUNTDOWN_DEFAULTS.per_week,
    home: typeof saved.home === "boolean" ? saved.home : COUNTDOWN_DEFAULTS.home,
  };
}

// Saves one or more settings after checking them against the plan.
export function setCountdown(state, plan, changes) {
  const ids = plan.phases.map((p) => p.id);
  const checks = {
    start: (v) => validDay(v),
    through: (v) => ids.includes(v),
    by: (v) => v === "start" || ids.includes(v),
    per_week: (v) => Number.isInteger(v) && v >= 1 && v <= 7,
    home: (v) => typeof v === "boolean",
  };
  for (const [key, value] of Object.entries(changes)) {
    if (!(key in checks)) throw new Error(`unknown countdown setting ${key}`);
    if (!checks[key](value)) throw new Error(`invalid ${key}: ${value}`);
  }
  const record = roleRecord(state, plan.id);
  record.countdown = { ...(record.countdown ?? {}), ...changes };
}

// Study days from today up to the day before the deadline, at `perWeek` days a week.
export function studyDays(daysLeft, perWeek) {
  if (daysLeft <= 0) return 0;
  return Math.floor(daysLeft / 7) * perWeek + Math.min(daysLeft % 7, perWeek);
}

// The work left in the chosen phases and the pace it needs by the deadline.
// `isDone(lessonId)` says whether you have completed a lesson. A competency's hours
// count in proportion to its lessons left. One with no lessons counts in full until
// you tick its assessment.
export function countdown(plan, record, today, isDone) {
  const settings = countdownSettings(plan, record);
  const upTo = plan.phases.findIndex((p) => p.id === settings.through);
  const phases = plan.phases.slice(0, upTo + 1);
  const byId = new Map(plan.modules.map((m) => [m.id, m]));
  const lessons = new Map();
  let hoursLeft = 0;
  for (const phase of phases) {
    for (const id of phase.modules) {
      const module = byId.get(id);
      if (!module) continue;
      const ids = module.lessons.map((l) => (typeof l === "string" ? l : l.id));
      for (const lessonId of ids) lessons.set(lessonId, isDone(lessonId));
      if (ids.length) hoursLeft += (module.hours * ids.filter((l) => !isDone(l)).length) / ids.length;
      else if (!record?.done?.[id]) hoursLeft += module.hours;
    }
  }
  const deadlinePhase = plan.phases.find((p) => p.id === settings.by);
  const deadline = deadlinePhase ? dayToDate(settings.start, deadlinePhase.days[1] + 1) : settings.start;
  const daysLeft = Math.round((toUtc(deadline) - toUtc(today)) / DAY_MS);
  const days = studyDays(daysLeft, settings.per_week);
  const left = [...lessons.values()].filter((done) => !done).length;
  return {
    settings,
    phases: phases.map((p) => p.id),
    deadline,
    daysLeft: Math.max(0, daysLeft),
    studyDays: days,
    lessonsLeft: left,
    lessonsTotal: lessons.size,
    hoursLeft: Math.round(hoursLeft * 10) / 10,
    lessonsPerStudyDay: days ? Math.round((left / days) * 10) / 10 : null,
    hoursPerStudyDay: days ? Math.round((hoursLeft / days) * 10) / 10 : null,
    status: left === 0 && hoursLeft === 0 ? "done" : daysLeft <= 0 ? "passed" : "running",
  };
}
