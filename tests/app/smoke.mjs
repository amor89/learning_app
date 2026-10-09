// Browser smoke test at iPhone width (390 x 844).
// Usage: node tests/app/smoke.mjs <base-url> [pyodide-url] [screenshot-dir]
// The base URL serves site/. The optional Pyodide URL points at a local copy of the
// Pyodide distribution, for environments that cannot reach the CDN.
import { mkdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE ?? "playwright");

const [base, pyodide, shots = "test-results"] = process.argv.slice(2);
if (!base) throw new Error("usage: smoke.mjs <base-url> [pyodide-url] [screenshot-dir]");
mkdirSync(shots, { recursive: true });
const query = pyodide ? `?pyodide=${encodeURIComponent(pyodide)}` : "";
const failures = [];
const check = (ok, message) => {
  console.log(`${ok ? "ok  " : "FAIL"} ${message}`);
  if (!ok) failures.push(message);
};

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

async function noHorizontalScroll(label) {
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  check(width <= 390, `${label}: page width ${width}px fits 390px`);
}

// Dashboard
await page.goto(`${base}${query}#/`);
await page.getByRole("heading", { name: "Dashboard" }).waitFor();
const index = JSON.parse(readFileSync(new URL("../../site/content/index.json", import.meta.url), "utf8"));
const trackCount = index.tracks.length;
const moduleCount = index.tracks.reduce((n, t) => n + t.modules.length, 0);
check(await page.locator(".card.track").count() === trackCount, `dashboard lists ${trackCount} tracks`);
check(await page.locator(".module-chip").count() === moduleCount, `dashboard shows ${moduleCount} module chips`);
await noHorizontalScroll("dashboard");
await page.screenshot({ path: `${shots}/01-dashboard.png`, fullPage: true });

// Lesson A3-L1: multiple choice with reasoning
await page.goto(`${base}${query}#/lesson/A3-L1`);
await page.getByRole("heading", { name: /Idempotent MERGE/ }).waitFor();
await noHorizontalScroll("lesson A3-L1");
await page.screenshot({ path: `${shots}/02-lesson-top.png` });
const ex = page.locator(".exercise");
await ex.locator("label.choice", { hasText: "last source row" }).click();
await ex.locator("label.choice", { hasText: "cannot tell which" }).click();
await ex.getByRole("button", { name: "Check" }).click();
check((await ex.locator(".feedback").textContent()).includes("no notion of 'last'"), "MCQ wrong answer shows its specific feedback");
check(await ex.getByRole("button", { name: "Show solution" }).isEnabled(), "solution unlocks after one attempt");
await ex.getByRole("button", { name: "Hint 1 of 3" }).click();
check(await ex.locator(".hints li").count() === 1, "first hint tier appears");
await ex.locator("label.choice", { hasText: "fails with an error" }).click();
await ex.getByRole("button", { name: "Check" }).click();
check((await ex.locator(".feedback").textContent()).includes("Correct"), "MCQ correct answer passes");
await page.locator("#practice").screenshot({ path: `${shots}/03-mcq.png` });

// Fill the gap
await page.getByRole("button", { name: "Exercise 2" }).click();
const gaps = page.locator(".exercise input.gap");
await gaps.nth(0).fill("whenMatchedUpdateAll");
await gaps.nth(1).fill("whenNotMatchedInsertAll");
await gaps.nth(2).fill("collect");
await page.getByRole("button", { name: "Check" }).click();
check((await page.locator(".feedback").textContent()).includes("execute()"), "fill-gap wrong answer shows its feedback");
await gaps.nth(2).fill("execute");
await page.getByRole("button", { name: "Check" }).click();
check((await page.locator(".feedback").textContent()).includes("Correct"), "fill-gap correct answer passes");
await noHorizontalScroll("fill gap");

// Spot the bug with a Python fix checker (AST rules only, no packages)
await page.getByRole("button", { name: "Exercise 4" }).click();
await page.getByRole("button", { name: "Line 6" }).click();
await page.getByRole("button", { name: "Check" }).click();
check((await page.locator(".feedback").textContent()).includes("Now fix"), "correct bug line unlocks the fix editor");
await page.screenshot({ path: `${shots}/04-spot-bug.png`, fullPage: false });

// Order
await page.getByRole("button", { name: "Exercise 6" }).click();
check(await page.locator(".order li").count() === 6, "order exercise lists six steps");
await noHorizontalScroll("order exercise");

// Worked example tabs
await page.getByRole("tab", { name: "Strong code" }).click();
check(await page.locator(".pane.strong").isVisible(), "strong code tab shows the strong pane");
await page.locator("#example").screenshot({ path: `${shots}/05-example.png` });

// Python exercise through Pyodide
if (pyodide) {
  await page.goto(`${base}${query}#/lesson/D3-L3`);
  await page.getByRole("heading", { name: /Mutable defaults/ }).waitFor();
  await page.getByRole("button", { name: "Exercise 5" }).click();
  const briefFirst = await page.evaluate(() => {
    const brief = document.querySelector(".exercise .brief");
    const editor = document.querySelector(".exercise textarea.editor");
    return Boolean(brief && editor && brief.compareDocumentPosition(editor) & Node.DOCUMENT_POSITION_FOLLOWING);
  });
  check(briefFirst, "code exercise shows its brief before the editor");
  check(await page.locator(".exercise .brief li").count() >= 3, "brief lists the steps and the checks");
  const area = page.locator("textarea.editor");
  await area.fill([
    "def compare_waves(current: dict[str, float | None], prior: dict[str, float | None], tolerance: float = 0.10) -> list[str]:",
    '    """Truthiness bug."""',
    "    flags: list[str] = []",
    "    for metric, current_pct in current.items():",
    "        prior_pct = prior.get(metric)",
    "        if current_pct and prior_pct:",
    "            if abs(current_pct - prior_pct) > tolerance:",
    "                flags.append(metric)",
    "    return flags",
  ].join("\n"));
  await page.getByRole("button", { name: "Run checks" }).click();
  await page.locator(".feedback.bad, .feedback.ok").waitFor({ timeout: 120_000 });
  const wrongText = await page.locator(".feedback").textContent();
  check(wrongText.includes("Test for None"), `Pyodide wrong answer gives rule feedback (${wrongText.trim().slice(0, 60)})`);
  await page.getByRole("button", { name: "Show solution" }).click();
  const solution = await page.locator(".solution .code").innerText();
  await area.fill(solution.split("\n").map((l) => l.replace(/^\s*\d+\s?/, "")).join("\n"));
  await page.getByRole("button", { name: "Run checks" }).click();
  await page.waitForFunction(() => document.querySelector(".feedback")?.textContent.includes("All checks passed"), null, { timeout: 60_000 }).catch(() => {});
  check((await page.locator(".feedback").textContent()).includes("All checks passed"), "Pyodide runs the reference solution and passes");
  await page.locator(".exercise").screenshot({ path: `${shots}/06-pyodide.png` });
}

// Finish D3-L3 by revealing solutions, then check the review deck
await page.goto(`${base}${query}#/lesson/D3-L3`);
await page.getByRole("heading", { name: /Mutable defaults/ }).waitFor();
for (let i = 1; i <= 6; i += 1) {
  await page.getByRole("button", { name: `Exercise ${i}`, exact: true }).click();
  const card = page.locator(".exercise");
  if (await card.locator(".pill.ok").count()) continue;
  await page.evaluate((id) => {
    const key = "learning-app.progress";
    const s = JSON.parse(localStorage.getItem(key));
    s.ex[id] = { ...(s.ex[id] ?? { hints: 0, passed: null, score: 0 }), attempts: 1, solution: true };
    localStorage.setItem(key, JSON.stringify(s));
  }, `D3-L3-E${i}`);
}
await page.reload();
await page.getByRole("heading", { name: /Mutable defaults/ }).waitFor();
check((await page.locator("#recap").textContent()).includes("Lesson complete"), "lesson completes when every exercise is done");
await page.goto(`${base}${query}#/review`);
await page.getByRole("button", { name: "Show answer" }).click();
await page.getByRole("button", { name: /^Good/ }).click();
check((await page.locator(".muted.small").first().textContent()).includes("Card 2 of 4"), "review moves to the next card after grading");
await page.screenshot({ path: `${shots}/07-review.png` });
await noHorizontalScroll("review");

// Dashboard reflects progress
await page.goto(`${base}${query}#/`);
const xp = await page.locator(".stat-value").first().textContent();
check(Number(xp) > 0, `dashboard shows earned XP (${xp})`);
await page.screenshot({ path: `${shots}/08-dashboard-after.png`, fullPage: true });

// Settings
await page.goto(`${base}${query}#/settings`);
check(await page.getByRole("button", { name: "Export progress" }).isVisible(), "settings offers export");
await noHorizontalScroll("settings");

check(errors.length === 0, `no console errors${errors.length ? `: ${errors.join(" | ")}` : ""}`);
await browser.close();
if (failures.length) {
  console.error(`${failures.length} check(s) failed`);
  process.exit(1);
}
console.log("All smoke checks passed.");
