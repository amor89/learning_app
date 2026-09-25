// Small DOM helpers. Content HTML comes from our own build, never from users.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs ?? {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "html") el.innerHTML = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else if (key === "dataset") Object.assign(el.dataset, value);
    else el.setAttribute(key, value === true ? "" : value);
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === undefined || child === null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function clear(el) {
  el.replaceChildren();
  return el;
}

export function pct(value) {
  return value === null || value === undefined ? "–" : `${Math.round(value * 100)}%`;
}

export function progressBar(share, label) {
  const value = Math.round((share ?? 0) * 100);
  return h(
    "div",
    { class: "bar", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": value, "aria-label": label },
    h("div", { class: "bar-fill", style: `width:${value}%` }),
  );
}

export function codeBlock(lines, options = {}) {
  const marks = new Map((options.notes ?? []).map((n, i) => [n.line, i + 1]));
  const selected = new Set(options.selected ?? []);
  const flagged = new Set(options.flagged ?? []);
  const rows = lines.map((html, i) => {
    const n = i + 1;
    const cls = ["ln", marks.has(n) && "annotated", selected.has(n) && "selected", flagged.has(n) && "flagged"]
      .filter(Boolean)
      .join(" ");
    const tag = options.onLine ? "button" : "div";
    const attrs = { class: cls, dataset: { line: n } };
    if (options.onLine) {
      attrs.type = "button";
      attrs["aria-pressed"] = selected.has(n) ? "true" : "false";
      attrs["aria-label"] = `Line ${n}`;
      attrs.onclick = () => options.onLine(n);
    }
    return h(
      tag,
      attrs,
      h("span", { class: "gutter", "aria-hidden": "true" }, marks.has(n) ? h("b", {}, marks.get(n)) : n),
      h("code", { html: html || " " }),
    );
  });
  return h("div", { class: `code ${options.className ?? ""}` }, rows);
}

export function plainCode(code) {
  return h("pre", { class: "code plain" }, h("code", {}, code));
}

export function notesList(notes) {
  if (!notes?.length) return null;
  return h(
    "ol",
    { class: "notes" },
    notes.map((n) => h("li", {}, h("span", { class: "note-line" }, `Line ${n.line}. `), h("span", { html: n.html }))),
  );
}

let toastTimer = null;
export function toast(message) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 2600);
}

export function editor(value, onChange, label = "Code editor") {
  const area = h("textarea", {
    class: "editor",
    spellcheck: "false",
    autocapitalize: "off",
    autocomplete: "off",
    autocorrect: "off",
    wrap: "off",
    rows: Math.min(18, Math.max(6, value.split("\n").length + 1)),
    "aria-label": label,
  });
  area.value = value;
  area.addEventListener("input", () => onChange(area.value));
  area.addEventListener("keydown", (event) => {
    if (event.key === "Tab" && !event.shiftKey) {
      event.preventDefault();
      area.setRangeText("    ", area.selectionStart, area.selectionEnd, "end");
      onChange(area.value);
    } else if (event.key === "Enter") {
      const start = area.value.lastIndexOf("\n", area.selectionStart - 1) + 1;
      const indent = area.value.slice(start).match(/^ */)[0];
      const extra = area.value.slice(start, area.selectionStart).trimEnd().endsWith(":") ? "    " : "";
      event.preventDefault();
      area.setRangeText(`\n${indent}${extra}`, area.selectionStart, area.selectionEnd, "end");
      onChange(area.value);
    }
  });
  return area;
}

export function downloadButtons(links, label) {
  if (!links) return h("p", { class: "muted small" }, "Handbook download not built yet.");
  return h(
    "div",
    { class: "downloads", role: "group", "aria-label": label },
    h("a", { class: "btn", href: links.pdf, download: "" }, "PDF"),
    h("a", { class: "btn secondary", href: links.docx, download: "" }, "Word"),
  );
}

export function tagChips(tags, bands) {
  const labels = new Map(bands.map((b) => [b.id, b.label]));
  return h("ul", { class: "chips", "aria-label": "Roadmap tags" }, tags.map((t) => h("li", { title: labels.get(t) ?? t }, t)));
}
