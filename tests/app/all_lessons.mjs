// Visit every lesson and every exercise at 390px: no horizontal scroll, no console errors.
// Usage: node tests/app/all_lessons.mjs <base-url>
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE ?? "playwright");
const base = process.argv[2];
const index = JSON.parse(readFileSync(new URL("../../site/content/index.json", import.meta.url), "utf8"));
const lessons = index.tracks.flatMap((t) => t.modules.flatMap((m) => m.lessons.map((l) => ({ ...l }))));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
const failures = [];

for (const lesson of lessons) {
  await page.goto(`${base}#/lesson/${lesson.id}`);
  // Hash navigation keeps the old page until the new lesson renders: wait for its title.
  await page.waitForFunction((title) => document.querySelector("h1")?.textContent === title, lesson.title);
  for (let i = 1; i <= lesson.exercises.length; i += 1) {
    await page.getByRole("button", { name: `Exercise ${i}`, exact: true }).click();
    await page.locator(".exercise").waitFor();
    const width = await page.evaluate(() => document.documentElement.scrollWidth);
    if (width > 390) failures.push(`${lesson.id} exercise ${i}: page width ${width}px`);
    const strayNull = await page.evaluate(() => {
      const walker = document.createTreeWalker(document.querySelector(".exercise"), NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) if (n.textContent.trim() === "null") return true;
      return false;
    });
    if (strayNull) failures.push(`${lesson.id} exercise ${i}: stray "null" text`);
  }
  for (const tab of ["Weak code", "Strong code"]) {
    await page.getByRole("tab", { name: tab }).click();
    const width = await page.evaluate(() => document.documentElement.scrollWidth);
    if (width > 390) failures.push(`${lesson.id} ${tab}: page width ${width}px`);
  }
}
await browser.close();
if (errors.length) failures.push(...errors.map((e) => `console: ${e}`));
console.log(`${lessons.length} lessons checked`);
if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log("No overflow and no console errors at 390px.");
