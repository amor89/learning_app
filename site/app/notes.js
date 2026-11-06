// Monthly notes: your own quick reference and deep dive for each roadmap month.
// Pure functions over the progress state and the cheat-sheet data, so Node can test them.

export const DEEP_DIVE_TEMPLATE = [
  "## Topic",
  "",
  "One idea from this month, in a sentence.",
  "",
  "## How it works",
  "",
  "## What I built",
  "",
  "## What surprised me",
  "",
  "## Trade-offs I would explain in an interview",
  "",
  "## Open questions",
  "",
].join("\n");

export function noteFor(state, stageId) {
  state.notes ??= {};
  state.notes[stageId] ??= { quick: "", deep: "", updated: null };
  return state.notes[stageId];
}

export function setNote(state, stageId, field, text, day) {
  if (field !== "quick" && field !== "deep") throw new Error(`unknown note field ${field}`);
  const note = noteFor(state, stageId);
  note[field] = text;
  note.updated = day;
  return note;
}

export function wordCount(text) {
  return (String(text ?? "").match(/[A-Za-z0-9][\w'.-]*/g) ?? []).length;
}

const ENTITIES = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&#x27;": "'" };

// The cheat-sheet HTML holds only inline Markdown: code, emphasis and links.
export function htmlToMarkdown(html) {
  return String(html ?? "")
    .replace(/<code>(.*?)<\/code>/gs, "`$1`")
    .replace(/<\/?(strong|b)>/g, "**")
    .replace(/<\/?(em|i)>/g, "*")
    .replace(/<[^>]+>/g, "")
    .replace(/&(amp|lt|gt|quot|#39|#x27);/g, (m) => ENTITIES[m]);
}

// The generated quick reference as Markdown, to start your own from.
export function quickrefMarkdown(sheets) {
  const lines = [];
  for (const sheet of sheets) {
    lines.push(`### ${sheet.id} ${sheet.title}`, "");
    for (const lesson of sheet.lessons) {
      lines.push(`- **${lesson.id} ${lesson.title}**: ${htmlToMarkdown(lesson.takeaway_html)}`);
      for (const card of lesson.recap) lines.push(`  - ${htmlToMarkdown(card.front_html)}: ${htmlToMarkdown(card.back_html)}`);
    }
    lines.push("");
  }
  return lines.join("\n").trimEnd() + "\n";
}

// One Markdown file for the month, ready for a GitHub repository.
export function exportMarkdown(month, note, lessons, day) {
  const section = (title, text, empty) => [`## ${title}`, "", String(text ?? "").trim() || empty, ""];
  return [
    `# ${month.title}`,
    "",
    `Learning notes. ${month.summary} Exported ${day}${note.updated ? `, last edited ${note.updated}` : ""}.`,
    "",
    "Lessons:",
    "",
    ...lessons.map((l) => `- ${l.id} ${l.title}`),
    "",
    ...section("Quick reference", note.quick, "_Not written yet._"),
    ...section("Deep dive", note.deep, "_Not written yet._"),
  ].join("\n");
}

// One line for the list of months.
export function noteStatus(note) {
  if (!note || (!note.quick.trim() && !note.deep.trim())) return "No notes yet";
  return `Quick reference ${wordCount(note.quick)} words · deep dive ${wordCount(note.deep)} words · edited ${note.updated}`;
}
