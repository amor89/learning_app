// Roadmap months: a one-page quick reference built from the lessons, and your own
// quick reference and deep dive, saved with your progress and exported as Markdown.
import * as notes from "./notes.js";
import * as store from "./store.js";
import { fileName, h, saveFile } from "./ui.js";

const SAVE_DELAY_MS = 400;

function notFound(stageId) {
  return h("section", { class: "page" }, h("h1", {}, "Not found"), h("p", {}, `Month ${stageId} does not exist.`), h("a", { href: "#/months" }, "All months"));
}

export function monthsView(app) {
  const months = app.index.months;
  return h(
    "section",
    { class: "page" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/" }, "Home")),
    h("h1", {}, "Monthly notes"),
    h("p", {}, "Your roadmap asks for a quick reference and a deep dive each month. Each month here has a one-page quick reference built from its lessons, and space for your own notes. Export them as Markdown for your GitHub repository."),
    h("ol", { class: "module-list" }, months.stages.map((m) => h("li", {}, h("a", { class: "card", href: `#/month/${m.id}` },
      h("strong", {}, m.title),
      h("span", { class: "muted small" }, m.summary),
      h("span", { class: "small" }, notes.noteStatus(app.state.notes?.[m.id])),
    )))),
  );
}

function quickrefLesson(lesson) {
  return h("section", { class: "qr-lesson" },
    h("h4", {}, h("a", { href: `#/lesson/${lesson.id}` }, `${lesson.id} ${lesson.title}`)),
    h("p", { class: "takeaway", html: lesson.takeaway_html }),
    h("ul", { class: "qr-facts" }, lesson.recap.map((c) => h("li", {}, h("strong", { html: c.front_html }), ": ", h("span", { html: c.back_html })))),
  );
}

// A notes box: a textarea that saves as you type, a word count, and a button that fills it.
function notesBox(app, month, field, { label, hint, fillLabel, fillText }) {
  const note = notes.noteFor(app.state, month.id);
  const status = h("span", { class: "muted small", "aria-live": "polite" });
  const count = () => `${notes.wordCount(note[field])} words`;
  status.textContent = count();
  const area = h("textarea", { class: "notes-editor", id: `notes-${field}`, rows: 12, spellcheck: "true", "aria-describedby": `notes-${field}-hint` });
  area.value = note[field];
  let timer = null;
  const save = () => {
    notes.setNote(app.state, month.id, field, area.value, store.today());
    app.save();
    status.textContent = `${count()} · saved`;
  };
  area.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(save, SAVE_DELAY_MS);
  });
  area.addEventListener("blur", () => {
    clearTimeout(timer);
    if (area.value !== note[field]) save();
  });
  const fillBtn = h("button", { type: "button", class: "btn secondary", onclick: async () => {
    if (area.value.trim() && !confirm("Replace what you have written?")) return;
    area.value = await fillText();
    save();
    area.focus();
  } }, fillLabel);
  return h("div", { class: "notes-box" },
    h("label", { class: "field-label", for: `notes-${field}` }, label),
    h("p", { class: "muted small", id: `notes-${field}-hint` }, hint),
    area,
    h("div", { class: "notes-actions" }, fillBtn, status),
  );
}

export async function monthView(app, stageId) {
  const month = app.index.months.stages.find((m) => m.id === stageId);
  if (!month) return notFound(stageId);
  const sheets = await Promise.all(month.modules.map((id) => app.sheet(id)));
  const lessons = sheets.flatMap((s) => s.lessons);
  const pdf = month.quickref ? fetch(month.quickref).then((r) => (r.ok ? r.blob() : null)).catch(() => null) : null;
  const exportBtn = h("button", { type: "button", class: "btn", onclick: () => {
    const md = notes.exportMarkdown(month, notes.noteFor(app.state, month.id), lessons, store.today());
    saveFile(Promise.resolve(new Blob([md], { type: "text/markdown" })), `learning-notes-${month.id}.md`);
  } }, "Save notes as Markdown");

  return h(
    "article",
    { class: "page month" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/" }, "Home"), " › ", h("a", { href: "#/months" }, "Monthly notes"), " › ", h("a", { href: `#/path/${app.index.months.pathway}/${month.id}` }, "Pathway stage")),
    h("h1", {}, month.title),
    h("p", {}, month.summary),
    h("h2", {}, "Your notes"),
    notesBox(app, month, "quick", {
      label: "Your quick reference",
      hint: "One page you would keep open while you work: the facts, formulas and defaults you look up. Start from the generated summary, then cut it down and add your own.",
      fillLabel: "Start from the generated summary",
      fillText: async () => notes.quickrefMarkdown(sheets),
    }),
    notesBox(app, month, "deep", {
      label: "Your deep dive",
      hint: "One idea from this month, explained in depth: how it works, what you built, and the trade-offs you would explain in an interview.",
      fillLabel: "Use the deep-dive template",
      fillText: async () => notes.DEEP_DIVE_TEMPLATE,
    }),
    h("div", { class: "actions" }, exportBtn),
    h("p", { class: "muted small" }, "Notes live in this browser with your progress. Export progress from Settings to keep a copy, or save the Markdown file to your repository."),
    h("h2", {}, "Quick reference from the lessons"),
    h("p", { class: "muted small" }, "Each lesson's takeaway and recap facts, on one printed page."),
    pdf ? h("div", { class: "actions" }, h("button", { type: "button", class: "btn secondary", onclick: () => saveFile(pdf, fileName(month.quickref)) }, "Save one-page PDF")) : null,
    sheets.map((sheet) => [h("h3", {}, `${sheet.id} ${sheet.title}`), sheet.lessons.map(quickrefLesson)]),
  );
}

export function monthLink(app, stageId, cls = "btn secondary") {
  const month = app.index.months?.stages.find((m) => m.id === stageId);
  return month ? h("a", { class: cls, href: `#/month/${month.id}` }, "Quick reference and notes") : null;
}
