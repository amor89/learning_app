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

// Replace an element's children. Skips null, undefined and false, which
// replaceChildren would otherwise insert as the text "null".
export function fill(el, ...children) {
  el.replaceChildren();
  append(el, children);
  return el;
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

// PDF and Word buttons. With a prefix the buttons name what they save, for example
// "Track B handbook: PDF", so they read clearly away from a heading.
export function downloadButtons(links, label, prefix = null) {
  if (!links) return h("p", { class: "muted small" }, "Handbook download not built yet.");
  const name = (kind) => (prefix ? `${prefix}: ${kind}` : kind);
  return h(
    "div",
    { class: "downloads", role: "group", "aria-label": label },
    h("button", { type: "button", class: "btn secondary", onclick: () => saveFile(links.pdf, fileName(links.pdf)) }, name("PDF")),
    h("button", { type: "button", class: "btn secondary", onclick: () => saveFile(links.docx, fileName(links.docx)) }, name("Word")),
  );
}

// Roadmap tags written out: "Months 1 to 3", not "M1-3". The full band label,
// with its theme, shows on hover.
export function tagText(tag, bands) {
  const label = bands.find((b) => b.id === tag)?.label;
  return label ? label.split(":")[0] : tag;
}

export function tagChips(tags, bands) {
  const labels = new Map(bands.map((b) => [b.id, b.label]));
  return h("ul", { class: "chips", "aria-label": "Roadmap tags" }, tags.map((t) => h("li", { title: labels.get(t) ?? t }, tagText(t, bands))));
}

// Links to a cheat sheet inside the app, so the tab bar and Back stay on screen.
// A PDF opened directly in an iPhone home-screen app has no way back.
export function sheetLink(hash, label = "Cheat sheet", cls = "btn secondary") {
  if (!hash) return null;
  return h("a", { class: cls, href: hash }, label);
}

// Saves a file without leaving the app: the share sheet where the device has one
// (iPhone: Save to Files), otherwise a download. source is a URL, or a promise of a
// Blob started early so the share call stays inside the tap that asked for it.
// Plain links to files are avoided: in an iPhone home-screen app they replace the
// app with no way back.
export async function saveFile(source, name) {
  try {
    const data = typeof source === "string"
      ? await fetch(source).then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.blob();
        })
      : await source;
    if (!data) throw new Error("not available");
    const file = new File([data], name, { type: data.type || "application/octet-stream" });
    if (navigator.canShare?.({ files: [file] })) {
      try {
        await navigator.share({ files: [file], title: name });
        return;
      } catch (error) {
        if (error?.name === "AbortError") return;
        // NotAllowedError: the tap expired while downloading. Fall back to a download.
      }
    }
    const url = URL.createObjectURL(data);
    const a = h("a", { href: url, download: name });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  } catch {
    toast("Could not save the file. Check your connection and try again.");
  }
}

export function fileName(url) {
  return url.split("/").pop();
}
