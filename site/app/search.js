// Search over site/content/search.json, which learnkit/search.py builds: key terms, lessons
// and recap cards. Pure functions, so Node can test them.

export const LIMITS = { terms: 8, lessons: 20, cards: 20 };
const WORD = /[\p{L}\p{N}_]/u;
const DIACRITICS = /[̀-ͯ]/g;

// Lower case without accents, one character for one character, so a position in the
// normalised text is the same position in the original.
export function normalise(text) {
  return [...text.toLowerCase()].map((c) => c.normalize("NFD").replace(DIACRITICS, "") || c).join("");
}

// The words of a query, without repeats. Single letters match too much, so they drop out.
export function queryTerms(query) {
  const words = normalise(query).split(/[^\p{L}\p{N}_]+/u).filter((w) => w.length > 1 || /\d/.test(w));
  return [...new Set(words)];
}

// Where term starts a word in hay, from position from on, or -1.
export function wordStart(hay, term, from = 0) {
  let at = hay.indexOf(term, from);
  while (at !== -1 && at > 0 && WORD.test(hay[at - 1])) at = hay.indexOf(term, at + 1);
  return at;
}

export function prepare(index) {
  const lessons = new Map(index.lessons.map((l) => [l.id, l]));
  const entry = (kind, item, title, fields) => ({ kind, item, title: normalise(title), fields: fields.map(([text, weight]) => [normalise(text), weight]) });
  return {
    lessons,
    entries: [
      ...index.terms.map((t) => entry("terms", t, t.term, [[t.term, 12]])),
      ...index.lessons.map((l) => entry("lessons", l, l.title, [[l.title, 8], [l.where, 3], [l.text, 1]])),
      ...index.cards.map((c) => entry("cards", c, c.front, [[c.front, 6], [c.back, 2]])),
    ],
  };
}

// Every query word must start a word somewhere in the entry. Title matches weigh most,
// a title that is the whole query, or starts with it, comes first, and the words found
// side by side count for more.
export function score(entry, terms, phrase) {
  let total = 0;
  for (const term of terms) {
    let best = 0;
    for (const [text, weight] of entry.fields) if (weight > best && wordStart(text, term) !== -1) best = weight;
    if (!best) return 0;
    total += best;
  }
  if (entry.title === phrase) total += 50;
  else if (entry.title.startsWith(phrase)) total += 20;
  else if (terms.length > 1 && entry.title.includes(phrase)) total += 10;
  // Several words found together, anywhere in the entry, beat the same words scattered.
  if (terms.length > 1 && entry.fields.some(([text]) => wordStart(text, phrase) !== -1)) total += 6;
  return total;
}

export function search(prepared, query) {
  const terms = queryTerms(query);
  const groups = { terms: [], lessons: [], cards: [] };
  if (!terms.length) return { terms, groups, total: 0 };
  const phrase = terms.join(" ");
  const scored = [];
  prepared.entries.forEach((entry, order) => {
    const s = score(entry, terms, phrase);
    if (s) scored.push({ entry, s, order });
  });
  scored.sort((a, b) => b.s - a.s || a.order - b.order);
  for (const { entry } of scored) groups[entry.kind].push(entry.item);
  const total = scored.length;
  for (const kind of Object.keys(groups)) groups[kind] = groups[kind].slice(0, LIMITS[kind]);
  return { terms, groups, total };
}

// The text split into plain and matched runs, for <mark>.
export function highlight(text, terms) {
  const hay = normalise(text);
  const ranges = [];
  for (const term of terms) {
    for (let at = wordStart(hay, term); at !== -1; at = wordStart(hay, term, at + term.length)) ranges.push([at, at + term.length]);
  }
  ranges.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const r of ranges) {
    const last = merged.at(-1);
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
    else merged.push([...r]);
  }
  const parts = [];
  let pos = 0;
  for (const [a, b] of merged) {
    if (a > pos) parts.push({ text: text.slice(pos, a), hit: false });
    parts.push({ text: text.slice(a, b), hit: true });
    pos = b;
  }
  if (pos < text.length) parts.push({ text: text.slice(pos), hit: false });
  return parts;
}

// A window of text around the whole query, or else its first matched word, cut at
// spaces, with ellipses where it was cut.
export function snippet(text, terms, radius = 70) {
  const hay = normalise(text);
  const phrase = terms.length > 1 ? wordStart(hay, terms.join(" ")) : -1;
  const hits = terms.map((t) => wordStart(hay, t)).filter((at) => at !== -1);
  const first = phrase !== -1 ? phrase : hits.length ? Math.min(...hits) : 0;
  let start = Math.max(0, first - radius);
  let end = Math.min(text.length, first + radius * 2);
  if (start > 0) start = text.indexOf(" ", start) + 1 || start;
  if (end < text.length) end = text.lastIndexOf(" ", end) > first ? text.lastIndexOf(" ", end) : end;
  return `${start > 0 ? "… " : ""}${text.slice(start, end).trim()}${end < text.length ? " …" : ""}`;
}
