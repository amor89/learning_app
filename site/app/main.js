// App entry: loads the content index, routes hash URLs and owns the progress state.
import * as store from "./store.js";
import { drillView, interviewView, taskView } from "./interview-view.js";
import { monthsView, monthView } from "./month-view.js";
import { backTarget, isRoot, visit } from "./nav.js";
import { placementView } from "./placement-view.js";
import { tabFor } from "./pathways.js";
import { roleView } from "./role-view.js";
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
let placementBank = null;
let roleBank = null;

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
  async roles() {
    roleBank ??= fetch("content/roles.json").then((r) => {
      if (!r.ok) throw new Error(`Role plans failed to load (${r.status}).`);
      return r.json();
    });
    try {
      return await roleBank;
    } catch (error) {
      roleBank = null;
      throw error;
    }
  },
  async placement() {
    placementBank ??= fetch("content/placement.json").then((r) => {
      if (!r.ok) throw new Error(`Placement quizzes failed to load (${r.status}).`);
      return r.json();
    });
    try {
      return await placementBank;
    } catch (error) {
      placementBank = null;
      throw error;
    }
  },
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

// The third element names the tab a page belongs to. Pages you reach from more than
// one tab (tracks, modules, lessons, sheets, notes, role plans) use null and stay
// under the tab you came from.
const ROUTES = [
  [/^#?\/?$/, () => dashboard(app), "home"],
  [/^#\/paths$/, () => pathwaysView(app), "paths"],
  [/^#\/path\/([\w-]+)(?:\/([\w-]+))?$/, (m) => pathwayView(app, m[1], m[2]), "paths"],
  [/^#\/library(?:\/(\w+))?$/, (m) => libraryView(app, m[1]), null],
  [/^#\/sheet\/([\w-]+)(?:\/([\w-]+))?$/, (m) => sheetView(app, m[1], m[2]), null],
  [/^#\/track\/(\w+)$/, (m) => trackView(app, m[1]), null],
  [/^#\/module\/(\w+)$/, (m) => moduleView(app, m[1]), null],
  [/^#\/lesson\/([\w-]+)$/, (m) => lessonView(app, m[1]), null],
  [/^#\/placement\/(\w+)$/, (m) => placementView(app, m[1]), null],
  [/^#\/months$/, () => monthsView(app), null],
  [/^#\/role\/([\w-]+)$/, (m) => roleView(app, m[1]), null],
  [/^#\/month\/([\w-]+)$/, (m) => monthView(app, m[1]), null],
  [/^#\/interview$/, () => interviewView(app), "interview"],
  [/^#\/interview\/drill$/, () => drillView(app), "interview"],
  [/^#\/interview\/task\/([\w-]+)$/, (m) => taskView(app, m[1]), "interview"],
  [/^#\/review$/, () => reviewView(app), "review"],
  [/^#\/settings$/, () => settingsView(app), "settings"],
];

let activeTab = "home";
let visited = [];
let titleWatch = null;

const backButton = document.querySelector(".topbar .back");
const barTitle = document.querySelector(".topbar-title");

// The header shows Back on every page but the five tab pages, and the page title
// once the page's own heading has scrolled under the header.
function updateHeader(hash, heading) {
  const root = isRoot(hash);
  backButton.hidden = root;
  const brand = root ? "Learning app" : "";
  barTitle.textContent = brand;
  titleWatch?.disconnect();
  if (!heading || !("IntersectionObserver" in window)) return;
  const top = document.querySelector(".topbar").offsetHeight;
  titleWatch = new IntersectionObserver(([entry]) => {
    barTitle.textContent = entry.isIntersecting ? brand : heading.textContent;
  }, { rootMargin: `-${top}px 0px 0px 0px` });
  titleWatch.observe(heading);
}

backButton.addEventListener("click", (event) => {
  event.preventDefault();
  const parent = [...document.querySelectorAll("#app .crumbs a")].at(-1)?.getAttribute("href");
  const target = backTarget(visited, parent);
  if (target === "history") history.back();
  else location.hash = target;
});

async function route() {
  const hash = location.hash || "#/";
  visited = visit(visited, hash);
  const match = ROUTES.map(([re, view, tab]) => [hash.match(re), view, tab]).find(([m]) => m);
  activeTab = tabFor(match?.[2], activeTab);
  document.querySelectorAll(".tabbar a").forEach((a) => a.setAttribute("aria-current", a.dataset.tab === activeTab ? "page" : "false"));
  try {
    const view = match ? await match[1](match[0]) : h("p", {}, "Page not found.");
    clear(root).append(view);
    const heading = root.querySelector("h1");
    document.title = heading ? `${heading.textContent} · Learning app` : "Learning app";
    window.scrollTo(0, 0);
    heading?.setAttribute("tabindex", "-1");
    heading?.focus({ preventScroll: true });
    updateHeader(hash, heading);
  } catch (error) {
    clear(root).append(h("section", { class: "page" }, h("h1", {}, "Something went wrong"), h("p", {}, error.message), h("a", { href: "#/" }, "Back to home")));
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
  watchForUpdates();
}

// A deploy shows on the next launch, because the service worker asks the network first.
// An app left open, or brought back from the background, checks the content version
// and offers a reload instead of reloading under you.
function watchForUpdates() {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") checkForUpdate();
  });
  if (!("serviceWorker" in navigator) || !(location.protocol === "https:" || location.hostname === "localhost")) return;
  const hadController = Boolean(navigator.serviceWorker.controller);
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (hadController) offerReload();
  });
  navigator.serviceWorker.register("sw.js", { updateViaCache: "none" }).catch(() => {});
}

async function checkForUpdate() {
  try {
    const response = await fetch("content/index.json", { cache: "no-store" });
    const latest = await response.json();
    if (latest.version !== app.index.version) offerReload();
    navigator.serviceWorker?.getRegistration().then((reg) => reg?.update()).catch(() => {});
  } catch {
    // Offline: nothing to compare against.
  }
}

function offerReload() {
  if (document.querySelector(".update-banner")) return;
  document.body.append(h("div", { class: "update-banner", role: "status" },
    h("span", {}, "A new version of the app is ready."),
    h("button", { type: "button", class: "btn", onclick: () => location.reload() }, "Reload"),
  ));
}

start();
