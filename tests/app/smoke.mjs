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

// Home
await page.goto(`${base}${query}#/`);
await page.getByRole("heading", { name: "Home" }).waitFor();
const index = JSON.parse(readFileSync(new URL("../../site/content/index.json", import.meta.url), "utf8"));
const trackCount = index.tracks.length;
const moduleCount = index.tracks.reduce((n, t) => n + t.modules.length, 0);
const first = index.pathways[0];
check(await page.locator(".stage-list > li").count() === Math.min(2, first.stages.length), `Home shows the current stage and the next one of ${first.title}`);
check((await page.locator(".stage-list .pill.ok").count()) === 1, "Home marks the current stage as Now");
check(await page.locator(".today .btn").count() === 1 && await page.locator("main .btn:not(.secondary):not(.ghost):not(.danger)").count() === 1, "Home has one filled button, Continue");
check(await page.locator(".quick-links a").count() >= 3, "Home shows the quick links");
check(await page.locator(".tabbar a[aria-current=page]").textContent() === "Home", "the Home tab is active on Home");
check(await page.locator(".tabbar .tab-icon").count() === 5, "every tab has an icon");
const firstLesson = first.stages.flatMap((s) => s.modules).map((id) => index.tracks.flatMap((t) => t.modules).find((m) => m.id === id)).find((m) => m.lessons.length).lessons[0];
check((await page.locator(".card.continue").getAttribute("href")) === `#/lesson/${firstLesson.id}`, `Continue opens the pathway's first lesson, ${firstLesson.id}`);
await noHorizontalScroll("Home");
await page.screenshot({ path: `${shots}/01-home.png`, fullPage: true });

// Library: tracks, module chips and downloads
await page.goto(`${base}${query}#/library`);
await page.getByRole("heading", { name: "All tracks and downloads" }).waitFor();
check(await page.locator(".card.track").count() === trackCount, `library lists ${trackCount} tracks`);
check(await page.locator(".module-chip").count() === moduleCount, `library shows ${moduleCount} module chips`);
await noHorizontalScroll("library");

// Pathways: the list, every pathway page, and choosing one
await page.getByRole("link", { name: "Paths" }).click();
await page.getByRole("heading", { name: "Pathways" }).waitFor();
check(await page.locator(".module-list > li").count() === index.pathways.length, `paths lists ${index.pathways.length} pathways`);
await noHorizontalScroll("pathways");
for (const pathway of index.pathways) {
  await page.goto(`${base}${query}#/path/${pathway.id}`);
  await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, pathway.title);
  check(await page.locator("details.path-stage").count() === pathway.stages.length, `${pathway.id} shows ${pathway.stages.length} stages`);
  await page.evaluate(() => document.querySelectorAll("details.path-stage").forEach((d) => (d.open = true)));
  await noHorizontalScroll(`pathway ${pathway.id}`);
}
await page.screenshot({ path: `${shots}/01b-pathway.png`, fullPage: true });
const last = index.pathways.at(-1);
await page.getByRole("button", { name: "Make this my pathway" }).click();
await page.getByText("Your pathway", { exact: true }).waitFor();
await page.goto(`${base}${query}#/`);
check((await page.locator(".pathway-card strong").textContent()) === last.title, `Home follows the chosen pathway, ${last.id}`);
await page.goto(`${base}${query}#/path/${first.id}/${first.stages[1].id}`);
await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, first.title);
check(await page.locator(`#stage-${first.stages[1].id}`).evaluate((d) => d.open), "a stage link opens that stage");
await page.locator(`#stage-${first.stages[1].id} .path-lesson`).first().click();
await page.waitForFunction(() => location.hash.startsWith("#/lesson/"));
check(await page.locator(".tabbar a[aria-current=page]").textContent() === "Paths", "a lesson opened from Paths keeps the Paths tab active");
await page.goto(`${base}${query}#/path/${first.id}/${first.stages[1].id}`);
await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, first.title);
await page.getByRole("button", { name: "Make this my pathway" }).click();
await page.getByText("Your pathway", { exact: true }).waitFor();

// Cheat sheets open inside the app, Back returns, and Save PDF hands over a real PDF.
// No link may point straight at a PDF: on an iPhone home-screen app it replaces the app with no way back.
async function noPdfLinks(label) {
  const direct = await page.locator('a[href$=".pdf"], a[href$=".docx"], a[href$=".ipynb"], a[target="_blank"]').count();
  check(direct === 0, `${label}: no link opens a file or a new tab directly`);
}
await page.goto(`${base}${query}#/module/B23`);
await page.getByRole("heading", { name: "B23 PyTorch foundations" }).waitFor();
await page.getByRole("link", { name: "B23 cheat sheet" }).click();
await page.waitForFunction(() => location.hash === "#/sheet/B23" && document.querySelector(".sheet-lesson"));
const b23 = index.tracks.flatMap((t) => t.modules).find((m) => m.id === "B23");
check(await page.locator(".sheet-lesson").count() === b23.lessons.length, `module sheet shows all ${b23.lessons.length} B23 lessons`);
check(await page.locator(".tabbar").isVisible(), "the tab bar stays on screen with a sheet open");
await noHorizontalScroll("cheat sheet B23");
await noPdfLinks("cheat sheet B23");
const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Save PDF" }).click()]);
const saved = readFileSync(await download.path());
check(download.suggestedFilename() === "cheatsheet-B23.pdf" && saved.subarray(0, 5).toString() === "%PDF-", "Save PDF delivers cheatsheet-B23.pdf");
await page.screenshot({ path: `${shots}/09-cheatsheet.png`, fullPage: true });
await page.getByRole("link", { name: "‹ Back" }).click();
await page.waitForFunction(() => location.hash === "#/module/B23");
check(true, "Back returns to the module page");
await noPdfLinks("module B23");

await page.goto(`${base}${query}#/path/${first.id}/${first.stages[1].id}`);
await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, first.title);
await noPdfLinks(`pathway ${first.id}`);
await page.locator(`#stage-${first.stages[1].id}`).getByRole("link", { name: "Stage cheat sheet" }).click();
await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, first.stages[1].title);
const stageModules = first.stages[1].modules.length;
check(await page.locator(".sheet h2").count() === stageModules, `stage sheet groups its ${stageModules} modules`);
await noHorizontalScroll("stage cheat sheet");

await page.goto(`${base}${query}#/lesson/B23-L1`);
await page.getByRole("heading", { name: /Tensors/ }).waitFor();
await page.getByRole("link", { name: "Open the B23 cheat sheet" }).click();
await page.waitForFunction(() => location.hash === "#/sheet/B23");
await page.getByRole("link", { name: "‹ Back" }).click();
await page.waitForFunction(() => location.hash === "#/lesson/B23-L1");
check(true, "Back from a sheet opened in a lesson returns to that lesson");
await page.goto(`${base}${query}#/lesson/B23-L6`);
await page.getByRole("heading", { name: /Dataset/ }).waitFor();
await noPdfLinks("lesson B23-L6 with a practical");
const [lab] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Save lab (PDF)" }).click()]);
check(lab.suggestedFilename() === "B23-L6.pdf", "Save lab delivers the practical PDF");
await page.goto(`${base}${query}#/library`);
await page.getByRole("heading", { name: "All tracks and downloads" }).waitFor();
check(await page.locator("details.sheets").count() === index.pathways.length, "library lists cheat sheets for every pathway");
await page.evaluate(() => document.querySelectorAll("details.sheets").forEach((d) => (d.open = true)));
await noHorizontalScroll("library with cheat sheets open");
await noPdfLinks("library");

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

// Home reflects progress
await page.goto(`${base}${query}#/`);
const xp = Number((await page.locator(".stats-line").textContent()).match(/^(\d+) XP/)?.[1]);
check(xp > 0, `Home shows earned XP (${xp})`);
await page.screenshot({ path: `${shots}/08-home-after.png`, fullPage: true });

// Placement quiz: Home offers it, a pass skips B0 and moves Continue on, a fail lists lessons
const placement = JSON.parse(readFileSync(new URL("../../site/content/placement.json", import.meta.url), "utf8"));
const quizB = placement.quizzes.find((q) => q.track === "B");
await page.goto(`${base}${query}#/`);
await page.getByRole("heading", { name: "Home" }).waitFor();
check(await page.locator(".placement-card").count() === 1, "Home offers the placement quiz while Continue points into B0");
await page.goto(`${base}${query}#/module/B0`);
await page.getByRole("heading", { name: /^B0 / }).waitFor();
check(await page.locator(".placement-card").count() === 1, "the start-here module page offers the placement quiz");
await page.locator(".placement-card a", { hasText: "Take the placement quiz" }).click();
await page.getByRole("heading", { name: /^Placement quiz/ }).waitFor();
check(await page.locator(".placement-q").count() === 10, "placement quiz shows ten questions");
await page.getByRole("button", { name: "See my result" }).click();
check((await page.locator("[role=status].feedback").textContent()).includes("10 left"), "the quiz asks for every answer first");
for (const q of quizB.questions) await page.locator(`input[name="pq-${q.id}"][value="${q.answer}"]`).check();
await page.getByRole("button", { name: "See my result" }).click();
await page.locator("#placement-result").waitFor();
check((await page.locator(".drill-score").textContent()) === "10 of 10", "a perfect quiz scores 10 of 10");
check(await page.locator(".placement-why .feedback.ok").count() === 10, "each answer shows as correct with its explanation");
await noHorizontalScroll("placement result");
await page.screenshot({ path: `${shots}/08b-placement.png`, fullPage: false });
await page.getByRole("button", { name: `Skip B0 and go to ${quizB.next.id}` }).click();
await page.waitForFunction((id) => location.hash === `#/module/${id}`, quizB.next.id);
await page.goto(`${base}${query}#/`);
await page.getByRole("heading", { name: "Home" }).waitFor();
const continueHref = await page.locator(".card.continue").getAttribute("href");
check(!continueHref.includes("B0-"), `after the skip, Continue passes over B0 (${continueHref})`);
check(await page.locator(".placement-card").count() === 0, "Home stops offering the quiz once taken");
await page.goto(`${base}${query}#/path/${first.id}/${first.stages[0].id}`);
await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, first.title);
check((await page.locator(".path-module", { hasText: "B0 " }).locator(".pill").textContent()) === "Skipped", "the pathway marks B0 as skipped");
const quizD = placement.quizzes.find((q) => q.track === "D");
await page.goto(`${base}${query}#/placement/D`);
await page.getByRole("heading", { name: /^Placement quiz/ }).waitFor();
for (const q of quizD.questions) {
  const wrong = q.options.find((o) => o.id !== q.answer).id;
  await page.locator(`input[name="pq-${q.id}"][value="${wrong}"]`).check();
}
await page.getByRole("button", { name: "See my result" }).click();
await page.locator("#placement-result").waitFor();
check((await page.locator("#placement-result").textContent()).includes("Start with D0"), "a failed quiz says to start at D0");
check(await page.locator("#placement-result .review-lessons li").count() === quizD.lessons.length, "a failed quiz lists the lessons to focus on");
check(await page.getByRole("button", { name: /^Skip D0/ }).count() === 0, "a failed quiz offers no skip");

// Monthly notes: the list, a month's one-page quick reference, notes that survive a reload, and exports
const months = index.months.stages;
await page.goto(`${base}${query}#/months`);
await page.getByRole("heading", { name: "Monthly notes" }).waitFor();
check(await page.locator(".module-list > li").count() === months.length, `monthly notes list ${months.length} months`);
const month = months[0];
await page.goto(`${base}${query}#/path/${index.months.pathway}/${month.id}`);
await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, index.pathways.find((p) => p.id === index.months.pathway).title);
check(await page.locator(`#stage-${month.id} a`, { hasText: "Quick reference and notes" }).count() === 1, "the pathway stage links to its month notes");
await page.goto(`${base}${query}#/month/${month.id}`);
await page.getByRole("heading", { name: month.title }).waitFor();
await page.locator(".qr-lesson").first().waitFor();
const monthLessons = month.modules.reduce((n, id) => n + index.tracks.flatMap((t) => t.modules).find((m) => m.id === id).lessons.length, 0);
check(await page.locator(".qr-lesson").count() === monthLessons, `the month shows a quick reference for its ${monthLessons} lessons`);
await page.getByRole("button", { name: "Start from the generated summary" }).click();
check((await page.locator("#notes-quick").inputValue()).startsWith(`### ${month.modules[0]} `), "the generated summary fills your quick reference");
await page.locator("#notes-deep").fill("Autograd builds a graph as I compute.");
await page.waitForTimeout(700);
await page.reload();
await page.getByRole("heading", { name: month.title }).waitFor();
check((await page.locator("#notes-deep").inputValue()) === "Autograd builds a graph as I compute.", "your deep dive survives a reload");
await noHorizontalScroll("month notes");
await page.screenshot({ path: `${shots}/08c-month.png`, fullPage: false });
const [markdown] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Save notes as Markdown" }).click()]);
const md = readFileSync(await markdown.path(), "utf8");
check(markdown.suggestedFilename() === `learning-notes-${month.id}.md` && md.includes("## Deep dive\n\nAutograd builds a graph"), "notes export as one Markdown file");
const [onePage] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Save one-page PDF" }).click()]);
check(onePage.suggestedFilename() === `quickref-${month.id}.pdf` && readFileSync(await onePage.path()).subarray(0, 5).toString() === "%PDF-", "the one-page quick reference saves as a PDF");
await noPdfLinks("month notes");

// Role plan: the EY pathway links to it, a self-assessment saves, and the summary shows the gap
const roles = JSON.parse(readFileSync(new URL("../../site/content/roles.json", import.meta.url), "utf8")).roles;
const plan = roles[0];
await page.goto(`${base}${query}#/path/${plan.pathway}`);
await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, index.pathways.find((p) => p.id === plan.pathway).title);
check(await page.locator(`a.card[href="#/role/${plan.id}"]`).count() === 1, "the role's pathway links to its role plan");
await page.locator(`a.card[href="#/role/${plan.id}"]`).click();
await page.getByRole("heading", { name: plan.title }).waitFor();
check(await page.locator(".role-module").count() === plan.modules.length, `the role plan lists ${plan.modules.length} competencies`);
check(await page.locator("details.path-stage").count() === plan.phases.length, `the role plan shows ${plan.phases.length} phases`);
const firstModule = plan.phases[0].modules[0];
const target = plan.modules.find((m) => m.id === firstModule).target;
await page.locator(`#role-${firstModule} .level-option`).nth(0).click();
check((await page.locator(`#role-${firstModule} .level-gap`).textContent()).startsWith(`${target - 1} level`), "rating Level 1 shows the gap to the target");
check((await page.locator(".stream-summary").textContent()).includes("1 of"), "the stream summary counts the rating");
await page.locator(`#role-${firstModule} .assessment input`).check();
await page.locator(".assumptions input").first().check();
await page.reload();
await page.getByRole("heading", { name: plan.title }).waitFor();
check(await page.locator(`#role-${firstModule} .level-option input`).nth(0).isChecked(), "your level survives a reload");
check(await page.locator(`#role-${firstModule} .assessment input`).isChecked(), "the assessment mark survives a reload");
check(await page.locator(".assumptions input").first().isChecked(), "a confirmed assumption survives a reload");
check(await page.locator(".pill.gap").count() === plan.modules.filter((m) => m.coverage === "gap").length, "competencies the app does not cover are marked");
await page.evaluate(() => document.querySelectorAll("details.path-stage").forEach((d) => (d.open = true)));
await noHorizontalScroll("role plan");
await page.screenshot({ path: `${shots}/08d-role.png`, fullPage: false });

// Interview practice: the hub, a timed drill to the end, and a timed task whose clock survives a reload
const bank = JSON.parse(readFileSync(new URL("../../site/content/interview.json", import.meta.url), "utf8"));
await page.getByRole("link", { name: "Interview" }).click();
await page.getByRole("heading", { name: "Interview practice" }).waitFor();
check(await page.locator(".interview .module-list > li").count() === bank.tasks.length, `interview lists ${bank.tasks.length} from-scratch tasks`);
check(await page.locator("#drill-topic option").count() === bank.topics.length + 1, `drill offers ${bank.topics.length} topics and all topics`);
await noHorizontalScroll("interview hub");
await page.selectOption("#drill-length", "5");
await page.getByRole("button", { name: "Start drill" }).click();
await page.getByRole("heading", { name: "Theory drill" }).waitFor();
check(/^\d+:\d\d$/.test(await page.locator(".clock").textContent()), "drill shows a countdown clock");
for (let i = 0; i < 5; i += 1) {
  const submit = page.getByRole("button", { name: "Submit" });
  if (await submit.count()) {
    await submit.click();
    check((await page.locator(".drill-review").textContent()).includes("Pick an option"), "submitting with no option asks for one");
    await page.locator(".choices input").first().check();
    await submit.click();
  } else {
    await page.getByRole("button", { name: "Show model answer" }).click();
    await page.locator(".points input").first().check();
  }
  check(await page.locator(".drill-review .taught a").count() > 0, `drill question ${i + 1} links to the lessons that teach it`);
  await noHorizontalScroll(`drill question ${i + 1}`);
  if (i === 0) await page.screenshot({ path: `${shots}/09-drill.png`, fullPage: true });
  await page.getByRole("button", { name: /Next question|See results/ }).click();
}
await page.getByRole("heading", { name: "Drill complete" }).waitFor();
check(await page.locator(".drill-results > li").count() === 5, "drill summary lists five answers");
const practice = await page.evaluate(() => JSON.parse(localStorage.getItem("learning-app.progress")).interview);
check(Object.keys(practice.theory).length === 5 && practice.drills.length === 1, "drill answers and the drill are saved");
await page.goto(`${base}${query}#/interview/task/${bank.tasks[0].id}`);
await page.getByRole("heading", { name: bank.tasks[0].title }).waitFor();
check(await page.locator("textarea.editor").count() === 0, "task editor stays hidden until the clock starts");
await page.getByRole("button", { name: "Start the clock" }).click();
await page.locator("textarea.editor").fill("# my draft\n");
await page.waitForTimeout(1200);
await page.reload();
await page.getByRole("heading", { name: bank.tasks[0].title }).waitFor();
check((await page.locator("textarea.editor").inputValue()) === "# my draft\n", "task code survives a reload");
check((await page.locator(".clock").textContent()) !== "0:00", "task clock keeps running across a reload");
check(await page.getByRole("button", { name: "Show solution" }).isDisabled(), "solution stays locked before an attempt");
await noHorizontalScroll("interview task");
await page.screenshot({ path: `${shots}/10-task.png`, fullPage: true });
if (pyodide) {
  const task = bank.tasks.find((t) => t.id === "layer-norm");
  await page.goto(`${base}${query}#/interview/task/${task.id}`);
  await page.getByRole("button", { name: "Start the clock" }).click();
  const area = page.locator("textarea.editor");
  await area.fill(["import numpy as np", "", "", "def layer_norm(x, gamma, beta, eps=1e-5):", "    return x", ""].join("\n"));
  await page.getByRole("button", { name: "Run checks" }).click();
  await page.locator("[role=status].feedback.bad, [role=status].feedback.ok").waitFor({ timeout: 120_000 });
  check(await page.locator("[role=status].feedback.bad").count() === 1, "Pyodide fails a wrong task answer");
  await page.getByRole("button", { name: "Show solution" }).click();
  check((await page.locator(".solution-box").textContent()).includes("def layer_norm"), "the solution shows after an attempt");
  check(await page.locator(".follow-up").count() === task.follow_ups.length, "follow-up questions show once the task ends");
}

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
