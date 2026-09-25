// Page views. Each view returns a DOM node for #app.
import { renderExercise } from "./exercises.js";
import * as store from "./store.js";
import {
  codeBlock,
  downloadButtons,
  h,
  notesList,
  pct,
  progressBar,
  tagChips,
} from "./ui.js";

function findModule(index, moduleId) {
  for (const track of index.tracks) {
    const module = track.modules.find((m) => m.id === moduleId);
    if (module) return { track, module };
  }
  return null;
}

function allLessons(index) {
  return index.tracks.flatMap((t) => t.modules.flatMap((m) => m.lessons.map((l) => ({ ...l, track: t, module: m }))));
}

function lessonStatus(state, lesson) {
  const done = lesson.exercises.filter((id) => store.isDone(state, id)).length;
  if (done === lesson.exercises.length) return "Complete";
  return done ? `${done} of ${lesson.exercises.length} done` : "Not started";
}

function notFound(what) {
  return h("section", { class: "page" }, h("h1", {}, "Not found"), h("p", {}, `${what} does not exist yet.`), h("a", { href: "#/" }, "Back to dashboard"));
}

// Dashboard ------------------------------------------------------------------

export function dashboard(app) {
  const { index, state } = app;
  const due = store.dueCards(state).length;
  const streak = store.currentStreak(state);
  const next = allLessons(index).find((l) => !store.lessonComplete(state, l));
  const bands = store.bandMastery(state, index).filter((b) => b.exercises > 0);
  const badges = Object.keys(state.badges).length;

  return h(
    "section",
    { class: "page" },
    h("h1", {}, "Dashboard"),
    h(
      "div",
      { class: "stats" },
      h("div", { class: "stat" }, h("span", { class: "stat-value" }, state.xp), h("span", { class: "stat-label" }, "XP")),
      h("div", { class: "stat" }, h("span", { class: "stat-value" }, streak), h("span", { class: "stat-label" }, `Day streak (best ${state.streak.best})`)),
      h("div", { class: "stat" }, h("span", { class: "stat-value" }, badges), h("span", { class: "stat-label" }, "Badges")),
      h("a", { class: "stat link", href: "#/review" }, h("span", { class: "stat-value" }, due), h("span", { class: "stat-label" }, "Cards due")),
    ),
    next
      ? h("a", { class: "card continue", href: `#/lesson/${next.id}` },
          h("span", { class: "muted small" }, `Continue · ${next.module.id} ${next.module.title}`),
          h("strong", {}, next.title),
        )
      : h("p", { class: "card" }, "Every published lesson is complete. New lessons arrive with each build phase."),
    h("h2", {}, "Tracks"),
    h(
      "div",
      { class: "grid" },
      index.tracks.map((track) => {
        const p = store.trackProgress(state, track);
        const published = track.modules.filter((m) => m.lessons.length).length;
        return h(
          "a",
          { class: "card track", href: `#/track/${track.id}` },
          h("span", { class: "track-id" }, `Track ${track.id}`),
          h("strong", {}, track.title),
          progressBar(p.share, `${track.title} progress`),
          h("span", { class: "muted small" }, `${p.done} of ${p.total} exercises · ${published} of ${track.modules.length} modules published`),
        );
      }),
    ),
    h("h2", {}, "Mastery by roadmap month"),
    bands.length
      ? h("ul", { class: "mastery" }, bands.map((b) =>
          h("li", {}, h("span", { class: "mastery-label" }, b.label), progressBar(b.mastery, b.label), h("span", { class: "mastery-value" }, pct(b.mastery))),
        ))
      : null,
    h("h2", {}, "Mastery by module"),
    h(
      "div",
      { class: "module-grid" },
      index.tracks.flatMap((t) => t.modules).map((m) => {
        const mastery = store.masteryOf(state, store.moduleExercises(m));
        const attrs = { class: `module-chip${m.lessons.length ? "" : " empty"}${state.badges[m.id] ? " badge" : ""}`, title: m.title };
        const inner = [h("span", { class: "chip-id" }, m.id), h("span", { class: "chip-value" }, m.lessons.length ? pct(mastery) : "soon")];
        return m.lessons.length ? h("a", { ...attrs, href: `#/module/${m.id}` }, inner) : h("span", attrs, inner);
      }),
    ),
    h("h2", {}, "Handbook"),
    h("p", { class: "muted" }, "The full handbook. Solutions sit in an appendix at the end."),
    downloadButtons(index.downloads, "Full handbook"),
    h("ul", { class: "plain-list" }, index.tracks.map((t) => h("li", {}, h("span", {}, `Track ${t.id}: ${t.title}`), downloadButtons(t.downloads, `Track ${t.id} handbook`)))),
  );
}

// Track and module -------------------------------------------------------------

export function trackView(app, trackId) {
  const track = app.index.tracks.find((t) => t.id === trackId);
  if (!track) return notFound(`Track ${trackId}`);
  const p = store.trackProgress(app.state, track);
  return h(
    "section",
    { class: "page" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/" }, "Dashboard")),
    h("h1", {}, `Track ${track.id}: ${track.title}`),
    h("p", {}, track.summary),
    progressBar(p.share, "Track progress"),
    h("p", { class: "muted small" }, `${p.done} of ${p.total} published exercises done`),
    downloadButtons(track.downloads, `Track ${track.id} handbook`),
    h(
      "ol",
      { class: "module-list" },
      track.modules.map((m) => {
        const mastery = store.masteryOf(app.state, store.moduleExercises(m));
        const body = [
          h("span", { class: "module-head" }, h("strong", {}, `${m.id} ${m.title}`), app.state.badges[m.id] ? h("span", { class: "pill ok" }, "Badge") : null),
          h("span", { class: "muted small" }, m.summary),
          tagChips(m.tags, app.index.bands),
          h("span", { class: "small" }, m.lessons.length ? `${m.lessons.length} lesson${m.lessons.length > 1 ? "s" : ""} · mastery ${pct(mastery)}` : "Coming in a later phase"),
        ];
        return h("li", {}, m.lessons.length ? h("a", { class: "card", href: `#/module/${m.id}` }, body) : h("div", { class: "card empty" }, body));
      }),
    ),
  );
}

export function moduleView(app, moduleId) {
  const found = findModule(app.index, moduleId);
  if (!found) return notFound(`Module ${moduleId}`);
  const { track, module } = found;
  return h(
    "section",
    { class: "page" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/" }, "Dashboard"), " › ", h("a", { href: `#/track/${track.id}` }, `Track ${track.id}`)),
    h("h1", {}, `${module.id} ${module.title}`),
    h("p", {}, module.summary),
    tagChips(module.tags, app.index.bands),
    h("h2", {}, "Download this module"),
    downloadButtons(module.downloads, `${module.id} handbook`),
    h("h2", {}, "Lessons"),
    module.lessons.length
      ? h("ol", { class: "lesson-list" }, module.lessons.map((l) =>
          h("li", {}, h("a", { class: "card", href: `#/lesson/${l.id}` }, h("strong", {}, l.title), h("span", { class: "muted small" }, `${lessonStatus(app.state, l)} · ${l.exercises.length} exercises · ${l.xp} XP`))),
        ))
      : h("p", {}, "Lessons for this module arrive in a later phase."),
  );
}

// Lesson ----------------------------------------------------------------------

function workedExample(example) {
  const panes = {
    weak: h("div", { class: "pane weak" }, h("h4", {}, "Weak"), codeBlock(example.weak.lines, { notes: example.weak.notes }), notesList(example.weak.notes)),
    strong: h("div", { class: "pane strong" }, h("h4", {}, "Strong"), codeBlock(example.strong.lines, { notes: example.strong.notes }), notesList(example.strong.notes)),
  };
  const wrap = h("div", { class: "compare show-weak" }, panes.weak, panes.strong);
  const tab = (key, label) =>
    h("button", {
      type: "button",
      role: "tab",
      class: "tab",
      "aria-selected": key === "weak" ? "true" : "false",
      onclick: (e) => {
        wrap.className = `compare show-${key}`;
        e.target.parentElement.querySelectorAll("button").forEach((b) => b.setAttribute("aria-selected", b === e.target ? "true" : "false"));
      },
    }, label);
  return h("div", {}, h("div", { class: "tabs", role: "tablist" }, tab("weak", "Weak code"), tab("strong", "Strong code")), wrap, h("div", { class: "takeaway", html: example.takeaway_html }));
}

function recapSection(app, lesson, meta) {
  const complete = store.lessonComplete(app.state, meta);
  return h(
    "div",
    {},
    h("div", { class: "recap" }, lesson.recap.map((c) => h("div", { class: "recap-card" }, h("p", { class: "front", html: c.front }), h("p", { class: "back", html: c.back })))),
    h("p", { class: complete ? "ok-text" : "muted small" }, complete ? "Lesson complete. These cards are in your review deck." : "Finish every exercise, by passing it or viewing its solution, to add these cards to your review deck."),
  );
}

function claimsSection(claims) {
  if (!claims.length) return null;
  return h(
    "details",
    { class: "claims" },
    h("summary", {}, "Sources and verification status"),
    h("ul", {}, claims.map((c) => h("li", {}, h("span", { class: `pill status-${c.status}` }, c.status), " ", c.claim, h("br"), h("span", { class: "muted small" }, c.source)))),
  );
}

export async function lessonView(app, lessonId) {
  const meta = allLessons(app.index).find((l) => l.id === lessonId);
  if (!meta) return notFound(`Lesson ${lessonId}`);
  const lesson = await app.lesson(lessonId);
  const exercises = lesson.exercises;
  let current = Math.max(0, exercises.findIndex((e) => !store.isDone(app.state, e.id)));
  const stage = h("div", { class: "stage" });
  const dots = h("ol", { class: "dots", "aria-label": "Exercises" });
  const recapHolder = h("div", {});

  const refresh = () => {
    if (store.lessonComplete(app.state, meta)) {
      store.completeLesson(app.state, lesson.id, lesson.recap.map((c) => c.id));
      for (const module of store.awardBadges(app.state, app.index)) app.toast(`Badge earned: ${module.id} ${module.title}`);
      app.save();
    }
    dots.replaceChildren(
      ...exercises.map((e, i) => {
        const s = app.state.ex[e.id];
        const cls = ["dot", i === current && "current", s?.passed && "passed", !s?.passed && s?.solution && "seen"].filter(Boolean).join(" ");
        return h("li", {}, h("button", { type: "button", class: cls, "aria-label": `Exercise ${i + 1}`, "aria-current": i === current ? "step" : null, onclick: () => show(i) }, i + 1));
      }),
    );
    recapHolder.replaceChildren(recapSection(app, lesson, meta));
  };

  const show = (i) => {
    current = i;
    stage.replaceChildren(
      renderExercise(app, exercises[i], i + 1, exercises.length, refresh),
      h("div", { class: "pager" },
        h("button", { type: "button", class: "btn secondary", disabled: i === 0, onclick: () => show(i - 1) }, "Previous"),
        h("button", { type: "button", class: "btn secondary", disabled: i === exercises.length - 1, onclick: () => show(i + 1) }, "Next"),
      ),
    );
    refresh();
  };
  show(current);

  const practical = lesson.practical
    ? h("section", { id: "practical" }, h("h2", {}, `Practical: ${lesson.practical.title}`), h("div", { html: lesson.practical.intro_html }),
        h("a", { class: "btn", href: lesson.practical.download, download: "" }, lesson.practical.platform === "databricks" ? "Download notebook (.ipynb)" : "Download lab (PDF)"))
    : null;

  return h(
    "article",
    { class: "page lesson" },
    h("nav", { class: "crumbs" }, h("a", { href: "#/" }, "Dashboard"), " › ", h("a", { href: `#/track/${meta.track.id}` }, `Track ${meta.track.id}`), " › ", h("a", { href: `#/module/${meta.module.id}` }, meta.module.id)),
    h("h1", {}, lesson.title),
    tagChips(lesson.tags, app.index.bands),
    h("nav", { class: "section-nav", "aria-label": "Lesson sections" },
      ["concept", "why", "example", "practice", "recap"].map((id) => h("a", { href: `#/lesson/${lesson.id}`, onclick: (e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }); } }, id === "why" ? "Why" : id[0].toUpperCase() + id.slice(1))),
    ),
    h("section", { id: "concept" }, h("h2", {}, "Concept"), h("div", { html: lesson.concept_html })),
    h("section", { id: "why" }, h("h2", {}, "Why it matters"), h("div", { html: lesson.why_html })),
    h("section", { id: "example" }, h("h2", {}, "Worked example"), workedExample(lesson.example)),
    h("section", { id: "practice" }, h("h2", {}, "Practice"), dots, stage),
    h("section", { id: "recap" }, h("h2", {}, "Recap"), recapHolder),
    practical,
    claimsSection(lesson.claims),
  );
}

// Review -----------------------------------------------------------------------

export async function reviewView(app) {
  const ids = store.dueCards(app.state);
  const page = h("section", { class: "page" }, h("h1", {}, "Daily review"));
  if (!ids.length) {
    const total = Object.keys(app.state.cards).length;
    page.append(h("p", {}, total ? "No cards due today. Come back tomorrow." : "Your deck is empty. Complete a lesson to add its recap cards."));
    return page;
  }
  const cards = await Promise.all(ids.map(async (id) => {
    const [lessonId, n] = id.split("#");
    const lesson = await app.lesson(lessonId);
    return { id, lesson, card: lesson.recap[Number(n)] };
  }));
  let i = 0;
  const box = h("div", {});
  const paint = () => {
    if (i >= cards.length) {
      box.replaceChildren(h("p", { class: "ok-text" }, `Done. You reviewed ${cards.length} card${cards.length > 1 ? "s" : ""}.`), h("a", { class: "btn", href: "#/" }, "Back to dashboard"));
      return;
    }
    const { id, lesson, card } = cards[i];
    const back = h("p", { class: "back", html: card.back, hidden: true });
    const grades = h("div", { class: "actions grades", hidden: true },
      Object.keys(store.GRADES).map((g) => {
        const preview = store.reviewCard(app.state.cards[id], g);
        return h("button", { type: "button", class: `btn ${g === "again" ? "secondary" : ""}`, onclick: () => {
          app.state.cards[id] = preview;
          store.markActive(app.state);
          app.save();
          i += 1;
          paint();
        } }, `${g[0].toUpperCase()}${g.slice(1)} · ${preview.interval}d`);
      }),
    );
    const reveal = h("button", { type: "button", class: "btn", onclick: () => { back.hidden = false; grades.hidden = false; reveal.hidden = true; grades.querySelector("button")?.focus(); } }, "Show answer");
    box.replaceChildren(
      h("p", { class: "muted small" }, `Card ${i + 1} of ${cards.length} · ${lesson.title}`),
      h("div", { class: "flashcard" }, h("p", { class: "front", html: card.front }), back),
      h("div", { class: "actions" }, reveal),
      grades,
    );
  };
  paint();
  page.append(box);
  return page;
}

// Settings ---------------------------------------------------------------------

export function settingsView(app) {
  const fileInput = h("input", { type: "file", accept: "application/json,.json", class: "sr-only", id: "import-file" });
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    try {
      const next = store.importJson(await file.text());
      if (!confirm("Replace your current progress with this file?")) return;
      app.replaceState(next);
      app.toast("Progress imported.");
    } catch (error) {
      app.toast(error.message);
    }
  });
  const exportBtn = h("button", { type: "button", class: "btn", onclick: () => {
    const blob = new Blob([store.exportJson(app.state)], { type: "application/json" });
    const a = h("a", { href: URL.createObjectURL(blob), download: `learning-progress-${store.today()}.json` });
    document.body.append(a);
    a.click();
    a.remove();
  } }, "Export progress");
  const theme = h("select", { id: "theme", onchange: (e) => app.setTheme(e.target.value) },
    [["auto", "Match the system"], ["light", "Light"], ["dark", "Dark"]].map(([v, t]) => h("option", { value: v, selected: app.state.settings.theme === v }, t)));

  return h(
    "section",
    { class: "page" },
    h("h1", {}, "Settings"),
    h("h2", {}, "Progress"),
    h("p", {}, "Progress lives in this browser only. Export it to keep a copy or to move it to another device."),
    h("div", { class: "actions" }, exportBtn, h("label", { class: "btn secondary", for: "import-file" }, "Import progress"), fileInput),
    h("h2", {}, "Appearance"),
    h("label", { class: "field-label", for: "theme" }, "Theme"),
    theme,
    h("h2", {}, "Reset"),
    h("button", { type: "button", class: "btn danger", onclick: () => {
      if (confirm("Delete all progress in this browser? Export first if you want a copy.")) {
        app.replaceState(store.emptyState());
        app.toast("Progress reset.");
      }
    } }, "Reset progress"),
    h("h2", {}, "About"),
    h("p", { class: "muted small" }, `Content version ${app.index.version}.`),
  );
}
