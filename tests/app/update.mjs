// Update test: a deploy reaches the app on the next launch, and an open app offers a reload.
// Serves a copy of site/ the way GitHub Pages does, with Cache-Control: max-age=600 and ETags,
// then changes files as a deploy would.
// Usage: node tests/app/update.mjs
import { createHash } from "node:crypto";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { extname, join, normalize } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE ?? "playwright");

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".webmanifest": "application/manifest+json", ".pdf": "application/pdf" };
const root = mkdtempSync(join(tmpdir(), "learning-site-"));
cpSync(new URL("../../site", import.meta.url), root, { recursive: true });

const server = createServer((req, res) => {
  const path = normalize(decodeURIComponent(new URL(req.url, "http://x").pathname)).replace(/^\/+/, "");
  const file = join(root, path === "" ? "index.html" : path);
  if (!file.startsWith(root)) return res.writeHead(403).end();
  let body;
  try {
    body = readFileSync(file);
  } catch {
    return res.writeHead(404).end();
  }
  const etag = `"${createHash("sha1").update(body).digest("hex")}"`;
  const headers = { "Cache-Control": "max-age=600", ETag: etag, "Content-Type": TYPES[extname(file)] ?? "application/octet-stream" };
  if (req.headers["if-none-match"] === etag) return res.writeHead(304, headers).end();
  res.writeHead(200, headers).end(body);
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://localhost:${server.address().port}/`;

const failures = [];
const check = (ok, message) => {
  console.log(`${ok ? "ok  " : "FAIL"} ${message}`);
  if (!ok) failures.push(message);
};

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));

try {
  await page.goto(base);
  await page.getByRole("heading", { name: "Dashboard" }).waitFor();
  await page.waitForFunction(() => navigator.serviceWorker.controller !== null, null, { timeout: 15_000 });
  check(true, "the service worker controls the app");

  // Deploy: new styles and a new content version.
  const marker = () => page.evaluate(() => getComputedStyle(document.body).getPropertyValue("--deploy-marker").trim());
  writeFileSync(join(root, "app/styles.css"), `${readFileSync(join(root, "app/styles.css"), "utf8")}\nbody { --deploy-marker: "v2"; }\n`);
  const indexPath = join(root, "content/index.json");
  writeFileSync(indexPath, readFileSync(indexPath, "utf8").replace(/"version":"[^"]+"/, '"version":"deployed-v2"'));

  // An open app, brought back to the front, offers a reload.
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  const banner = await page.locator(".update-banner").waitFor({ timeout: 5_000 }).then(() => true, () => false);
  check(banner, "an open app offers a reload once a deploy lands");

  // One launch picks up the deploy, despite max-age=600.
  await page.reload();
  await page.getByRole("heading", { name: "Dashboard" }).waitFor();
  check((await marker()) === '"v2"', `one reload shows the new styles (marker ${JSON.stringify(await marker())})`);
  check(await page.locator(".update-banner").count() === 0, "no reload banner after the reload");

  // Offline, the app still opens from the cache.
  await context.setOffline(true);
  await page.reload();
  const offline = await page.getByRole("heading", { name: "Dashboard" }).waitFor({ timeout: 10_000 }).then(() => true, () => false);
  check(offline, "the app opens offline from the cache");
  await context.setOffline(false);
  check(errors.length === 0, `no page errors${errors.length ? `: ${errors.join(" | ")}` : ""}`);
} finally {
  await browser.close();
  server.close();
  rmSync(root, { recursive: true, force: true });
}
if (failures.length) {
  console.error(`${failures.length} check(s) failed`);
  process.exit(1);
}
console.log("All update checks passed.");
