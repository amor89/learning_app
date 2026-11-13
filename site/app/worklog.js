// Work log: a line or two per win, decision, lesson learned or piece of feedback,
// dated and optionally tagged to a role plan phase, exported as Markdown for reviews.
// Pure functions over the progress state, so Node can test them.

export const KINDS = [
  { id: "win", label: "Win" },
  { id: "decision", label: "Decision" },
  { id: "lesson", label: "Lesson learned" },
  { id: "feedback", label: "Feedback" },
];

export const MAX_TEXT = 1000;

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function validDay(day) {
  if (typeof day !== "string" || !ISO_DAY.test(day)) return false;
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toISOString().slice(0, 10) === day;
}

export function kindLabel(kind) {
  return KINDS.find((k) => k.id === kind)?.label ?? kind;
}

export function logRecord(state) {
  state.worklog ??= { entries: [], seq: 0 };
  state.worklog.entries ??= [];
  state.worklog.seq ??= 0;
  return state.worklog;
}

// Adds an entry after checking it. Text and impact are trimmed; phase is optional.
export function addEntry(state, { day, kind, text, impact = "", phase = null }) {
  if (!validDay(day)) throw new Error(`invalid date ${day}`);
  if (!KINDS.some((k) => k.id === kind)) throw new Error(`unknown kind ${kind}`);
  const body = String(text ?? "").trim();
  if (!body) throw new Error("write what happened");
  if (body.length > MAX_TEXT) throw new Error(`keep it under ${MAX_TEXT} characters`);
  const effect = String(impact ?? "").trim();
  if (effect.length > MAX_TEXT) throw new Error(`keep the impact under ${MAX_TEXT} characters`);
  if (phase !== null && (typeof phase !== "string" || !phase)) throw new Error(`invalid phase ${phase}`);
  const log = logRecord(state);
  log.seq += 1;
  const entry = { id: `w${log.seq}`, day, kind, text: body, impact: effect, phase };
  log.entries.push(entry);
  return entry;
}

export function removeEntry(state, id) {
  const log = logRecord(state);
  const before = log.entries.length;
  log.entries = log.entries.filter((e) => e.id !== id);
  return log.entries.length < before;
}

function seqOf(entry) {
  return Number(entry.id.slice(1)) || 0;
}

// Newest first: by date, then by the order you added them. Optionally one kind only.
export function listEntries(state, kind = "all") {
  return logRecord(state).entries
    .filter((e) => kind === "all" || e.kind === kind)
    .slice()
    .sort((a, b) => (a.day === b.day ? seqOf(b) - seqOf(a) : a.day < b.day ? 1 : -1));
}

export function counts(state) {
  const result = { all: 0 };
  for (const k of KINDS) result[k.id] = 0;
  for (const e of logRecord(state).entries) {
    result.all += 1;
    if (e.kind in result) result[e.kind] += 1;
  }
  return result;
}

export function monthName(day) {
  const [y, m] = day.split("-").map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

function oneLine(text) {
  return text.replace(/\s*\n\s*/g, " ");
}

// The log as Markdown, grouped by month, newest month first, for a review or a 1:1.
export function toMarkdown(state, today) {
  const entries = listEntries(state);
  const lines = ["# Work log", "", `Exported ${today}. ${entries.length} entr${entries.length === 1 ? "y" : "ies"}.`, ""];
  const tally = counts(state);
  lines.push(KINDS.map((k) => `${k.label}: ${tally[k.id]}`).join(" · "), "");
  let month = null;
  for (const e of entries) {
    const name = monthName(e.day);
    if (name !== month) {
      month = name;
      if (lines.at(-1) !== "") lines.push("");
      lines.push(`## ${name}`, "");
    }
    const tag = e.phase ? ` (${e.phase})` : "";
    lines.push(`- **${e.day} · ${kindLabel(e.kind)}${tag}**: ${oneLine(e.text)}`);
    if (e.impact) lines.push(`  - Impact: ${oneLine(e.impact)}`);
  }
  if (!entries.length) lines.push("No entries yet.");
  return `${lines.join("\n").trimEnd()}\n`;
}
