// Progress storage in localStorage, with XP, streaks, badges, mastery and SM-2 review.
// All state lives under one versioned key. Export and import use the same JSON shape.

const KEY = "learning-app.progress";
const VERSION = 1;
const HINT_PENALTY = 0.25;
const MIN_XP_SHARE = 0.25;

export function today(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function addDays(day, n) {
  const [y, m, d] = day.split("-").map(Number);
  return today(new Date(y, m - 1, d + n));
}

export function emptyState() {
  return {
    v: VERSION,
    xp: 0,
    streak: { current: 0, best: 0, last: null },
    days: {},
    ex: {},
    lessons: {},
    badges: {},
    cards: {},
    settings: { theme: "auto" },
  };
}

function safeStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function load() {
  const storage = safeStorage();
  try {
    const raw = storage?.getItem(KEY);
    if (!raw) return emptyState();
    return migrate(JSON.parse(raw));
  } catch {
    return emptyState();
  }
}

export function save(state) {
  try {
    safeStorage()?.setItem(KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

export function migrate(data) {
  if (!data || typeof data !== "object" || data.v !== VERSION) {
    throw new Error("This file is not a progress export from this app.");
  }
  return { ...emptyState(), ...data, settings: { ...emptyState().settings, ...data.settings } };
}

// Activity and streak -------------------------------------------------------

export function markActive(state, xp = 0, day = today()) {
  const s = state.streak;
  if (s.last !== day) {
    s.current = s.last === addDays(day, -1) ? s.current + 1 : 1;
    s.best = Math.max(s.best, s.current);
    s.last = day;
  }
  state.days[day] = (state.days[day] ?? 0) + xp;
}

export function currentStreak(state, day = today()) {
  const last = state.streak.last;
  return last === day || last === addDays(day, -1) ? state.streak.current : 0;
}

// Exercises -----------------------------------------------------------------

export function exState(state, id) {
  state.ex[id] ??= { attempts: 0, hints: 0, passed: null, solution: false, score: 0 };
  return state.ex[id];
}

export function recordHint(state, id) {
  const e = exState(state, id);
  e.hints = Math.min(3, e.hints + 1);
}

export function recordSolutionSeen(state, id) {
  exState(state, id).solution = true;
}

export function scoreFor(e) {
  if (e.solution) return MIN_XP_SHARE;
  return Math.max(MIN_XP_SHARE, 1 - HINT_PENALTY * e.hints);
}

// Returns the XP earned by this attempt (0 unless it is the first pass).
export function recordAttempt(state, id, passed, baseXp, day = today()) {
  const e = exState(state, id);
  e.attempts += 1;
  if (!passed || e.passed) {
    markActive(state, 0, day);
    return 0;
  }
  e.passed = day;
  e.score = scoreFor(e);
  const earned = Math.round(baseXp * e.score);
  state.xp += earned;
  markActive(state, earned, day);
  return earned;
}

export function isDone(state, id) {
  const e = state.ex[id];
  return Boolean(e && (e.passed || e.solution));
}

// Lessons, badges and mastery ------------------------------------------------

export function lessonComplete(state, lesson) {
  return lesson.exercises.every((id) => isDone(state, id));
}

// Marks the lesson complete and adds its recap cards to the review deck.
export function completeLesson(state, lessonId, cardIds, day = today()) {
  state.lessons[lessonId] ??= { done: day };
  for (const id of cardIds) {
    state.cards[id] ??= { ef: 2.5, n: 0, interval: 0, due: day };
  }
}

export function masteryOf(state, exerciseIds) {
  if (exerciseIds.length === 0) return null;
  const total = exerciseIds.reduce((sum, id) => sum + (state.ex[id]?.passed ? state.ex[id].score : 0), 0);
  return total / exerciseIds.length;
}

export function moduleExercises(module) {
  return module.lessons.flatMap((l) => l.exercises);
}

export function awardBadges(state, index, day = today()) {
  const earned = [];
  for (const track of index.tracks) {
    for (const module of track.modules) {
      if (state.badges[module.id] || module.lessons.length === 0) continue;
      if (module.lessons.every((l) => lessonComplete(state, l))) {
        state.badges[module.id] = day;
        earned.push(module);
      }
    }
  }
  return earned;
}

export function bandMastery(state, index) {
  const byBand = {};
  for (const track of index.tracks) {
    for (const module of track.modules) {
      const ids = moduleExercises(module);
      for (const tag of module.tags) {
        byBand[tag] ??= [];
        byBand[tag].push(...ids);
      }
    }
  }
  return index.bands.map((band) => ({
    ...band,
    exercises: (byBand[band.id] ?? []).length,
    mastery: masteryOf(state, byBand[band.id] ?? []),
  }));
}

export function trackProgress(state, track) {
  const ids = track.modules.flatMap(moduleExercises);
  const done = ids.filter((id) => isDone(state, id)).length;
  return { done, total: ids.length, share: ids.length ? done / ids.length : 0 };
}

// Spaced repetition (SM-2) --------------------------------------------------

export const GRADES = { again: 1, hard: 3, good: 4, easy: 5 };

export function reviewCard(card, grade, day = today()) {
  const q = GRADES[grade];
  if (q === undefined) throw new Error(`unknown grade ${grade}`);
  const next = { ...card };
  if (q < 3) {
    next.n = 0;
    next.interval = 1;
  } else {
    next.n = card.n + 1;
    next.interval = next.n === 1 ? 1 : next.n === 2 ? 6 : Math.round(card.interval * card.ef);
  }
  next.ef = Math.max(1.3, card.ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
  next.due = addDays(day, next.interval);
  return next;
}

export function dueCards(state, day = today()) {
  return Object.entries(state.cards)
    .filter(([, card]) => card.due <= day)
    .map(([id]) => id)
    .sort();
}

// Export and import -----------------------------------------------------------

export function exportJson(state) {
  return JSON.stringify({ ...state, exportedAt: new Date().toISOString() }, null, 2);
}

export function importJson(text) {
  const { exportedAt, ...data } = JSON.parse(text);
  return migrate(data);
}
