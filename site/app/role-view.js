// Role plan view: dated phases, the competencies with your self-assessed level against
// the target, the lessons that teach each one, what the app does not cover yet, and the
// assumptions to confirm.
import * as paths from "./pathways.js";
import * as role from "./role.js";
import * as store from "./store.js";
import { fill, h, pct, progressBar } from "./ui.js";

const COVERAGE = {
  full: { text: "Covered", cls: "ok" },
  partial: { text: "Partly covered", cls: "" },
  gap: { text: "Not in the app yet", cls: "gap" },
};

function longDate(day) {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

function notFound(roleId) {
  return h("section", { class: "page" }, h("h1", {}, "Not found"), h("p", {}, `Role plan ${roleId} does not exist.`), h("a", { href: "#/paths" }, "Pathways"));
}

function levelName(plan, level) {
  return plan.levels.find((l) => l.level === level)?.name ?? "";
}

function assumedText(module) {
  if (!module.assumed.length) return null;
  const [low, high] = [module.assumed[0], module.assumed.at(-1)];
  return low === high ? `your brief assumes Level ${low}` : `your brief assumes Level ${low} to ${high}`;
}

function checkbox(label, checked, onchange) {
  return h("label", { class: "check-line" }, h("input", { type: "checkbox", checked, onchange: (e) => onchange(e.target.checked) }), h("span", {}, label));
}

function statusLine(plan, today) {
  const day = role.planDay(plan.start, today);
  const last = plan.phases.at(-1).days[1];
  if (day < 1) return `Starts on ${longDate(plan.start)}, in ${1 - day} day${day === 0 ? "" : "s"}.`;
  if (day > last) return `The ${last}-day plan ended on ${longDate(role.dayToDate(plan.start, last))}.`;
  const phase = role.currentPhase(plan, today);
  return `Day ${day} of ${last}: Phase ${phase.id.slice(1)}, ${phase.name}.`;
}

function moduleCard(app, plan, module, record, lessonMeta, onChange) {
  const cover = COVERAGE[module.coverage];
  const progress = role.lessonProgress(app.state, module.lessons, lessonMeta);
  const gapLine = h("p", { class: "small level-gap" });
  const paintGap = () => {
    const gap = role.levelGap(record, module);
    gapLine.className = `small level-gap${gap > 0 ? " below" : ""}`;
    gapLine.textContent = gap === null
      ? "Rate yourself to see the gap to the target."
      : gap > 0 ? `${gap} level${gap > 1 ? "s" : ""} below the target.` : "At or above the target.";
  };
  const picker = h("div", { class: "level-picker", role: "radiogroup", "aria-label": `${module.id} your level` },
    plan.levels.map((lv) => h("label", { class: "level-option" },
      h("input", { type: "radio", name: `level-${module.id}`, value: lv.level, checked: record.levels[module.id] === lv.level, onchange: () => {
        role.setLevel(app.state, plan.id, module.id, lv.level, store.today());
        app.save();
        paintGap();
        onChange();
      } }),
      h("span", {}, h("b", {}, lv.level), ` ${lv.name}`),
    )),
  );
  paintGap();
  return h("li", { class: "card role-module", id: `role-${module.id}` },
    h("div", { class: "module-head" },
      h("strong", {}, `${module.id} ${module.title}`),
      h("span", { class: `pill ${cover.cls}` }, cover.text),
    ),
    h("p", { class: "muted small" }, [
      `${module.stream} · target Level ${module.target} ${levelName(plan, module.target)}`,
      assumedText(module) ? ` · ${assumedText(module)}` : "",
      ` · about ${module.hours} hours`,
      module.prerequisites.length ? ` · after ${module.prerequisites.join(", ")}` : "",
    ].join("")),
    h("p", { class: "field-label small" }, "Your level now"),
    picker,
    gapLine,
    h("ul", { class: "outcomes" }, module.outcomes.map((o) => h("li", {}, o))),
    module.lessons.length
      ? h("div", { class: "role-lessons" },
          h("p", { class: "small" }, `Lessons that teach it: ${progress.done} of ${progress.total} complete`),
          h("ul", { class: "plain-list" }, module.lessons.map((l) => {
            const meta = lessonMeta.get(l.id);
            const done = meta && store.lessonComplete(app.state, meta);
            return h("li", {}, h("a", { href: `#/lesson/${l.id}` }, `${l.id} ${l.title}`), done ? h("span", { class: "pill ok" }, "Done") : null);
          })),
        )
      : null,
    module.gaps_html ? h("p", { class: "small gap-note" }, h("strong", {}, "Not covered yet: "), h("span", { html: module.gaps_html })) : null,
    h("div", { class: "assessment" },
      h("p", { class: "small" }, h("strong", {}, "Assessment: "), h("span", { html: module.assessment_html })),
      checkbox("Assessment done", Boolean(record.done[module.id]), (on) => {
        role.toggle(app.state, plan.id, "done", module.id, on);
        app.save();
      }),
    ),
  );
}

export async function roleView(app, roleId) {
  const bank = await app.roles();
  const plan = bank.roles.find((r) => r.id === roleId);
  if (!plan) return notFound(roleId);
  const record = role.roleRecord(app.state, plan.id);
  const today = store.today();
  const lessonMeta = new Map(app.index.tracks.flatMap((t) => t.modules.flatMap((m) => m.lessons.map((l) => [l.id, l]))));
  const current = role.currentPhase(plan, today);
  const chosen = paths.chosenPathway(app.index, app.state);
  const summary = h("ul", { class: "mastery stream-summary" });
  const paintSummary = () => fill(summary, role.streamSummary(plan, record).map((s) => h("li", {},
    h("span", { class: "mastery-label" }, `${s.stream} · ${s.rated} of ${s.modules} rated${s.below.length ? ` · below target: ${s.below.join(", ")}` : ""}`),
    progressBar(s.level === null ? 0 : Math.min(1, s.level / s.target), `${s.stream} level against target`),
    h("span", { class: "mastery-value" }, s.level === null ? "–" : `${s.level.toFixed(1)}/${s.target.toFixed(1)}`),
  )));
  paintSummary();
  const byId = new Map(plan.modules.map((m) => [m.id, m]));

  return h(
    "article",
    { class: "page role" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/" }, "Dashboard"), " › ", h("a", { href: `#/path/${plan.pathway}` }, "Pathway")),
    h("h1", {}, plan.title),
    h("p", { class: "muted small", html: plan.status_html }),
    h("div", { class: "card pathway-card" },
      h("strong", {}, statusLine(plan, today)),
      h("span", { class: "muted small" }, `Version ${plan.version} · ${plan.phases.length} phases · ${plan.modules.length} competencies`),
      h("div", { class: "actions" },
        h("a", { class: "btn secondary", href: `#/path/${plan.pathway}` }, "Open the pathway"),
        chosen.id === plan.pathway ? null : h("button", { type: "button", class: "btn ghost", onclick: () => {
          paths.choosePathway(app.state, plan.pathway);
          app.replaceState(app.state);
        } }, "Make it my pathway"),
      ),
    ),
    h("h2", {}, "Self-assessment"),
    h("p", { class: "muted small" }, "Rate yourself on each competency below. The bars compare your mean level with the mean target for each stream."),
    h("dl", { class: "levels" }, plan.levels.flatMap((l) => [h("dt", {}, `${l.level} ${l.name}`), h("dd", {}, l.meaning)])),
    summary,
    h("h2", {}, "Phases"),
    h("ol", { class: "path-stages" }, plan.phases.map((phase) => {
      const dates = role.phaseDates(plan.start, phase);
      return h("li", {}, h("details", { class: "path-stage", id: `phase-${phase.id}`, open: phase === current },
        h("summary", {},
          h("span", { class: "module-head" }, h("strong", {}, `${phase.id} ${phase.name}`), phase === current ? h("span", { class: "pill ok" }, "Now") : null),
          h("span", { class: "muted small" }, `Days ${phase.days[0]} to ${phase.days[1]} · ${longDate(dates.from)} to ${longDate(dates.to)}`),
        ),
        h("p", { class: "small" }, h("strong", {}, "Success: "), h("span", { html: phase.success_html })),
        checkbox("Success criterion met", Boolean(record.phases[phase.id]), (on) => {
          role.toggle(app.state, plan.id, "phases", phase.id, on);
          app.save();
        }),
        h("ol", { class: "module-list" }, phase.modules.map((id) => moduleCard(app, plan, byId.get(id), record, lessonMeta, paintSummary))),
      ));
    })),
    plan.assumptions.length ? h("h2", {}, "Assumptions to confirm") : null,
    plan.assumptions.length
      ? h("ul", { class: "plain-list assumptions" }, plan.assumptions.map((text, i) => h("li", {}, checkbox(text, Boolean(record.assumptions[i]), (on) => {
          role.toggle(app.state, plan.id, "assumptions", String(i), on);
          app.save();
        }))))
      : null,
    h("p", { class: "muted small" }, `Self-assessment progress: ${pct(Object.keys(record.levels).length / plan.modules.length)} of competencies rated.`),
  );
}

// A link card for the dashboard and the pathway page.
export function roleCard(app, roleRef) {
  return h("a", { class: "card continue", href: `#/role/${roleRef.id}` },
    h("span", { class: "muted small" }, "Role plan"),
    h("strong", {}, roleRef.title),
    h("span", { class: "small" }, "Phases, self-assessment and the gaps the app does not cover yet"),
  );
}
