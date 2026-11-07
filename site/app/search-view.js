// The search page: one box, results grouped into key terms, lessons and recap cards.
import * as s from "./search.js";
import { fill, h } from "./ui.js";

const WAIT_MS = 120;

function marked(text, terms) {
  return s.highlight(text, terms).map((p) => (p.hit ? h("mark", {}, p.text) : p.text));
}

function lessonRef(prepared, id) {
  const lesson = prepared.lessons.get(id);
  return h("span", { class: "muted small" }, lesson ? `${lesson.id} ${lesson.title}` : id);
}

function group(title, items, render) {
  if (!items.length) return null;
  return [h("h2", {}, title), h("ul", { class: "search-list" }, items.map((item) => h("li", {}, render(item))))];
}

function results(prepared, query) {
  const found = s.search(prepared, query);
  const { terms, groups } = found;
  if (!terms.length) {
    return h("p", { class: "muted" }, "Type a word or two. Search covers every lesson, its recap cards and the key terms it defines.");
  }
  if (!found.total) return h("p", { class: "muted" }, `Nothing matches "${query.trim()}". Try fewer words, or the start of a word.`);
  const shown = groups.terms.length + groups.lessons.length + groups.cards.length;
  return [
    h("p", { class: "muted small search-count" }, found.total > shown ? `${found.total} matches. The best ${shown} show here.` : `${found.total} match${found.total === 1 ? "" : "es"}`),
    group("Key terms", groups.terms, (t) => h("a", { class: "search-hit", href: `#/lesson/${t.lesson}` },
      h("strong", {}, marked(t.term, terms)), lessonRef(prepared, t.lesson))),
    group("Lessons", groups.lessons, (l) => h("a", { class: "search-hit", href: `#/lesson/${l.id}` },
      h("strong", {}, marked(l.title, terms)),
      h("span", { class: "muted small" }, l.where),
      h("span", { class: "small" }, marked(s.snippet(l.text, terms), terms)))),
    group("Recap cards", groups.cards, (c) => h("a", { class: "search-hit", href: `#/lesson/${c.lesson}` },
      h("strong", {}, marked(c.front, terms)),
      h("span", { class: "small" }, marked(c.back, terms)),
      lessonRef(prepared, c.lesson))),
  ];
}

export async function searchView(app, query = "") {
  const prepared = await app.search();
  const box = h("div", { class: "search-results", "aria-live": "polite" });
  let timer = null;
  const input = h("input", {
    type: "search",
    id: "search-q",
    class: "search-input",
    value: query,
    placeholder: "Search lessons, cards and terms",
    autocomplete: "off",
    autocapitalize: "off",
    spellcheck: "false",
    enterkeyhint: "search",
    oninput: () => {
      clearTimeout(timer);
      timer = setTimeout(run, WAIT_MS);
    },
  });
  // The query lives in the URL, so Back from a result returns to the same results.
  const run = () => {
    const q = input.value;
    history.replaceState(history.state, "", `#/search${q.trim() ? `?q=${encodeURIComponent(q)}` : ""}`);
    fill(box, results(prepared, q));
  };
  fill(box, results(prepared, query));
  setTimeout(() => {
    if (!query) input.focus();
  }, 0);
  return h(
    "section",
    { class: "page search" },
    h("h1", {}, "Search"),
    h("form", { role: "search", onsubmit: (e) => { e.preventDefault(); input.blur(); run(); } },
      h("label", { class: "sr-only", for: "search-q" }, "Search"), input),
    box,
  );
}
