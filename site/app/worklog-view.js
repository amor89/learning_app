// Work log page: add a win, decision, lesson learned or feedback in a line or two,
// filter by kind, delete, and save the whole log as Markdown for a review.
import * as role from "./role.js";
import * as store from "./store.js";
import { fill, h, saveFile, toast } from "./ui.js";
import * as log from "./worklog.js";

function longDate(day) {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

// The role plan phase that holds a day, using your own start date. Null before the
// start or after the plan ends.
export function phaseOn(plan, record, day) {
  const start = role.countdownSettings(plan, record).start;
  const n = role.planDay(start, day);
  return plan.phases.find((p) => n >= p.days[0] && n <= p.days[1])?.id ?? null;
}

async function loadPlan(app) {
  const ref = (app.index.roles ?? [])[0];
  if (!ref) return null;
  try {
    const bank = await app.roles();
    return bank.roles.find((r) => r.id === ref.id) ?? null;
  } catch {
    return null;
  }
}

function entryCard(entry, onDelete) {
  return h("li", { class: "card log-entry", id: `log-${entry.id}` },
    h("div", { class: "module-head" },
      h("strong", {}, log.kindLabel(entry.kind)),
      h("span", { class: "muted small" }, [longDate(entry.day), entry.phase ? ` · ${entry.phase}` : ""].join("")),
    ),
    h("p", { class: "log-text" }, entry.text),
    entry.impact ? h("p", { class: "small log-text" }, h("strong", {}, "Impact: "), entry.impact) : null,
    h("button", { type: "button", class: "btn ghost", onclick: () => onDelete(entry) }, "Delete"),
  );
}

export async function worklogView(app) {
  const plan = await loadPlan(app);
  const record = plan ? app.state.roles?.[plan.id] : undefined;
  let filter = "all";
  const list = h("ol", { class: "module-list log-list" });
  const chips = h("div", { class: "log-filter", role: "group", "aria-label": "Show" });

  const paint = () => {
    const tally = log.counts(app.state);
    fill(chips, [{ id: "all", label: "All" }, ...log.KINDS].map((k) => h("button", {
      type: "button",
      class: "log-chip",
      "aria-pressed": String(filter === k.id),
      onclick: () => {
        filter = k.id;
        paint();
      },
    }, `${k.label} ${tally[k.id]}`)));
    const entries = log.listEntries(app.state, filter);
    fill(list, entries.length
      ? entries.map((e) => entryCard(e, (entry) => {
          if (!confirm(`Delete this ${log.kindLabel(entry.kind).toLowerCase()}?`)) return;
          log.removeEntry(app.state, entry.id);
          app.save();
          paint();
        }))
      : h("li", { class: "muted small" }, filter === "all" ? "Nothing logged yet. Add your first entry above." : "No entries of this kind yet."));
  };

  const today = store.today();
  const dayInput = h("input", { id: "log-day", type: "date", value: today, max: today, required: true });
  const kindSelect = h("select", { id: "log-kind" }, log.KINDS.map((k) => h("option", { value: k.id }, k.label)));
  const text = h("textarea", { id: "log-text", rows: 3, maxlength: log.MAX_TEXT, placeholder: "What happened, in a line or two" });
  const impact = h("input", { id: "log-impact", type: "text", maxlength: log.MAX_TEXT, placeholder: "Optional: the result, with a number if you have one" });
  const phaseSelect = plan
    ? h("select", { id: "log-phase" },
        h("option", { value: "" }, "None"),
        plan.phases.map((p) => h("option", { value: p.id }, `${p.id} ${p.name}`)))
    : null;
  const syncPhase = () => {
    if (phaseSelect && dayInput.value) phaseSelect.value = phaseOn(plan, record, dayInput.value) ?? "";
  };
  dayInput.addEventListener("change", syncPhase);
  syncPhase();

  const form = h("form", { class: "card log-form", onsubmit: (e) => {
    e.preventDefault();
    try {
      log.addEntry(app.state, {
        day: dayInput.value,
        kind: kindSelect.value,
        text: text.value,
        impact: impact.value,
        phase: phaseSelect?.value || null,
      });
    } catch (error) {
      toast(`Not added: ${error.message}.`);
      return;
    }
    app.save();
    text.value = "";
    impact.value = "";
    filter = "all";
    paint();
    toast("Added to your work log.");
  } },
    h("div", { class: "log-fields" },
      h("label", { class: "field-label small", for: "log-day" }, "Date"), dayInput,
      h("label", { class: "field-label small", for: "log-kind" }, "Kind"), kindSelect,
      phaseSelect ? h("label", { class: "field-label small", for: "log-phase" }, "Phase") : null, phaseSelect,
    ),
    h("label", { class: "field-label small", for: "log-text" }, "What happened"), text,
    h("label", { class: "field-label small", for: "log-impact" }, "Impact"), impact,
    h("div", { class: "actions" }, h("button", { type: "submit", class: "btn" }, "Add to log")),
  );

  const exportBtn = h("button", { type: "button", class: "btn secondary", onclick: () => {
    const md = log.toMarkdown(app.state, store.today());
    saveFile(Promise.resolve(new Blob([md], { type: "text/markdown" })), `work-log-${store.today()}.md`);
  } }, "Save as Markdown");

  paint();
  return h(
    "section",
    { class: "page worklog" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/" }, "Home")),
    h("h1", {}, "Work log"),
    h("p", { class: "muted small" }, "Note each win, decision, lesson learned or piece of feedback the week it happens, in a line or two. Add the result with a number where you have one. At review time, save the log as Markdown. It stays in this browser with the rest of your progress, so export your progress from Settings to back it up."),
    form,
    h("h2", {}, "Entries"),
    chips,
    list,
    h("div", { class: "actions" }, exportBtn),
  );
}
