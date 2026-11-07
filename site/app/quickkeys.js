// Quick keys: a row of coding keys above the on-screen keyboard while a code editor has
// focus on a touch screen. applyKey is pure, so Node can test it.

export const INDENT = "    ";
const PAIRS = { "(": ")", "[": "]", "{": "}", '"': '"', "'": "'" };

// The keys in the row, in order: [label, key, accessible name].
export const KEYS = [
  ["⇥", "tab", "Indent"],
  ["⇤", "dedent", "Remove indent"],
  ["(", "(", "Brackets"],
  ["[", "[", "Square brackets"],
  ["{", "{", "Braces"],
  [":", ":", "Colon"],
  ['"', '"', "Double quotes"],
  ["'", "'", "Single quotes"],
  ["=", "=", "Equals"],
  ["_", "_", "Underscore"],
  ["#", "#", "Hash"],
  [".", ".", "Full stop"],
  [",", ",", "Comma"],
];

function lineStart(text, pos) {
  return text.lastIndexOf("\n", pos - 1) + 1;
}

// Applies one quick key to text with a selection from start to end.
// Returns the new text and selection.
//   - A bracket or quote with no selection inserts the pair and puts the cursor inside it.
//     With a selection, it wraps the selection.
//   - "tab" inserts four spaces, or indents every selected line.
//   - "dedent" removes up to four leading spaces from the current or every selected line.
//   - Any other key inserts itself in place of the selection.
export function applyKey(text, start, end, key) {
  if (key === "tab" || key === "dedent") {
    const multiLine = text.slice(start, end).includes("\n");
    if (key === "tab" && !multiLine) {
      return { text: text.slice(0, start) + INDENT + text.slice(end), start: start + INDENT.length, end: start + INDENT.length };
    }
    const from = lineStart(text, start);
    const lineEnd = text.indexOf("\n", end) === -1 ? text.length : text.indexOf("\n", end);
    const lines = text.slice(from, lineEnd).split("\n");
    let shiftFirst = 0;
    let total = 0;
    const changed = lines.map((line, i) => {
      if (key === "tab") {
        if (i === 0) shiftFirst = INDENT.length;
        total += INDENT.length;
        return INDENT + line;
      }
      const removed = line.match(/^ {0,4}/)[0].length;
      if (i === 0) shiftFirst = -Math.min(removed, start - from);
      total -= removed;
      return line.slice(removed);
    });
    const next = text.slice(0, from) + changed.join("\n") + text.slice(lineEnd);
    const newStart = start + shiftFirst;
    const newEnd = start === end ? newStart : end + total;
    return { text: next, start: newStart, end: newEnd };
  }
  const close = PAIRS[key];
  if (close) {
    const inner = text.slice(start, end);
    const next = text.slice(0, start) + key + inner + close + text.slice(end);
    return inner
      ? { text: next, start: start + 1, end: start + 1 + inner.length }
      : { text: next, start: start + 1, end: start + 1 };
  }
  const next = text.slice(0, start) + key + text.slice(end);
  return { text: next, start: start + key.length, end: start + key.length };
}

// The row's top edge in page coordinates, so it sits on the visual viewport's lower
// edge, just above the on-screen keyboard. null when the browser has no visualViewport.
export function barTop(vv, barHeight) {
  if (!vv) return null;
  return Math.max(0, Math.round(vv.offsetTop + vv.height - barHeight));
}

// True on phones and tablets, where the on-screen keyboard lacks these keys.
export function wantsQuickKeys(win = globalThis) {
  return Boolean(win.matchMedia?.("(pointer: coarse)").matches);
}

// Shows the row while any code editor (textarea.editor) has focus on a touch screen,
// so the editor keeps focus and the on-screen keyboard stays open.
export function installQuickKeys(doc = document, win = window) {
  if (!wantsQuickKeys(win)) return null;
  let target = null;
  const bar = doc.createElement("div");
  bar.className = "quick-keys";
  bar.setAttribute("role", "toolbar");
  bar.setAttribute("aria-label", "Coding keys");
  bar.hidden = true;
  for (const [label, key, name] of KEYS) {
    const button = doc.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.setAttribute("aria-label", name);
    // pointerdown only keeps focus in the editor. The key acts on click, so a swipe that
    // scrolls the row does not type anything.
    button.addEventListener("pointerdown", (event) => event.preventDefault());
    button.addEventListener("click", () => {
      if (!target) return;
      const next = applyKey(target.value, target.selectionStart, target.selectionEnd, key);
      target.value = next.text;
      target.setSelectionRange(next.start, next.end);
      target.dispatchEvent(new Event("input", { bubbles: true }));
      if (doc.activeElement !== target) target.focus({ preventScroll: true });
    });
    bar.append(button);
  }
  doc.body.append(bar);

  // Sit just above the on-screen keyboard: the visual viewport ends where it starts.
  // Only one of top and bottom may be set, or the row stretches between them.
  const place = () => {
    const top = barTop(win.visualViewport, bar.offsetHeight);
    bar.style.top = top === null ? "auto" : `${top}px`;
    bar.style.bottom = top === null ? "0px" : "auto";
  };
  win.visualViewport?.addEventListener("resize", () => target && place());
  win.visualViewport?.addEventListener("scroll", () => target && place());

  doc.addEventListener("focusin", (event) => {
    if (!(event.target instanceof win.HTMLTextAreaElement) || !event.target.classList.contains("editor")) return;
    target = event.target;
    bar.hidden = false;
    place();
  });
  // A tap on the row can blur the editor for a moment on some phones, so wait before hiding.
  doc.addEventListener("focusout", (event) => {
    if (event.target !== target) return;
    win.setTimeout(() => {
      if (doc.activeElement === target || bar.contains(doc.activeElement)) return;
      target = null;
      bar.hidden = true;
    }, 150);
  });
  return bar;
}
