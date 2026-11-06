// App entry: loads the content index, routes hash URLs and owns the progress state.
import * as store from "./store.js";
import { drillView, interviewView, taskView } from "./interview-view.js";
import { clear, h, toast } from "./ui.js";
import {
  dashboard,
  lessonView,
  libraryView,
  moduleView,
  pathwaysView,
  pathwayView,
  reviewView,
  settingsView,
  sheetView,
  trackView,
} from "./views.js";

const root = document.getElementById("app");
const lessons = new Map();
const sheets = new Map();
let interviewBank = null;

const app = {
  index: null,
  state: store.load(),
  drafts: {},
  toast,
  save() {
    if (!store.save(app.state)) toast("Could not save progress in this browser. Export it from Settings.");
  },
  replaceState(next) {
    app.state = next;
    app.save();
    applyTheme();
    route();
  },
  setTheme(theme) {
    app.state.settings.theme = theme;
    app.save();
    applyTheme();
  },
  drill: null,
  async interview() {
    interviewBank ??= fetch("content/interview.json").then((r) => {
      if (!r.ok) throw new Error(`Interview practice failed to load (${r.status}).`);
      return r.json();
    });
    try {
      return await interviewBank;
    } catch (error) {
      interviewBank = null;
      throw error;
    }
  },
  async sheet(id) {
    if (!sheets.has(id)) {
      sheets.set(id, fetch(`content/sheets/${id}.json`).then((r) => {
        if (!r.ok) throw new Error(`Cheat sheet ${id} failed to load (${r.status}).`);
        return r.json();
      }));
    }
    try {
      return await sheets.get(id);
    } catch (error) {
      sheets.delete(id);
      throw error;
    }
  },
  async lesson(id) {
    if (!lessons.has(id)) {
      lessons.set(id, fetch(`content/lessons/${id}.json`).then((r) => {
        if (!r.ok) throw new Error(`Lesson ${id} failed to load (${r.status}).`);
        return r.json();
      }));
    }
    try {
      return await lessons.get(id);
    } catch (error) {
      lessons.delete(id);
      throw error;
    }
  },
};

function applyTheme() {
  const theme = app.state.settings.theme;
  if (theme === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.dataset.theme = theme;
}

const ROUTES = [
  [/^#?\/?$/, () => dashboard(app), "home"],
  [/^#\/paths$/, () => pathwaysView(app), "paths"],
  [/^#\/path\/([\w-]+)(?:\/([\w-]+))?$/, (m) => pathwayView(app, m[1], m[2]), "paths"],
  [/^#\/library$/, () => libraryView(app), "home"],
  [/^#\/sheet\/([\w-]+)(?:\/([\w-]+))?$/, (m) => sheetView(app, m[1], m[2]), "home"],
  [/^#\/track\/(\w+)$/, (m) => trackView(app, m[1]), "home"],
  [/^#\/module\/(\w+)$/, (m) => moduleView(app, m[1]), "home"],
  [/^#\/lesson\/([\w-]+)$/, (m) => lessonView(app, m[1]), "home"],
  [/^#\/interview$/, () => interviewView(app), "interview"],
  [/^#\/interview\/drill$/, () => drillView(app), "interview"],
  [/^#\/interview\/task\/([\w-]+)$/, (m) => taskView(app, m[1]), "interview"],
  [/^#\/review$/, () => reviewView(app), "review"],
  [/^#\/settings$/, () => settingsView(app), "settings"],
];

async function route() {
  const hash = location.hash || "#/";
  const match = ROUTES.map(([re, view, tab]) => [hash.match(re), view, tab]).find(([m]) => m);
  document.querySelectorAll(".tabbar a").forEach((a) => a.setAttribute("aria-current", match && a.dataset.tab === match[2] ? "page" : "false"));
  try {
    const view = match ? await match[1](match[0]) : h("p", {}, "Page not found.");
    clear(root).append(view);
    const heading = root.querySelector("h1");
    document.title = heading ? `${heading.textContent} · Learning app` : "Learning app";
    window.scrollTo(0, 0);
    heading?.setAttribute("tabindex", "-1");
    heading?.focus({ preventScroll: true });
  } catch (error) {
    clear(root).append(h("section", { class: "page" }, h("h1", {}, "Something went wrong"), h("p", {}, error.message), h("a", { href: "#/" }, "Back to dashboard")));
  }
}

async function start() {
  applyTheme();
  try {
    const response = await fetch("content/index.json", { cache: "no-cache" });
    app.index = await response.json();
  } catch {
    clear(root).append(h("p", {}, "Could not load the course. Check your connection and reload."));
    return;
  }
  window.addEventListener("hashchange", route);
  await route();
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost")) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

start();
