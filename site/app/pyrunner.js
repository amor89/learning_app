// Runs Python checks in a Web Worker and restarts the worker after a timeout.
import { FIRST_LOAD_TIMEOUT_MS, RUN_TIMEOUT_MS, pyodideBase } from "./config.js";

let worker = null;
let warm = false;
let nextId = 1;
const pending = new Map();

function startWorker() {
  worker = new Worker(new URL("./pyworker.js", import.meta.url), { type: "module" });
  worker.onmessage = ({ data }) => {
    const job = pending.get(data.id);
    if (!job) return;
    pending.delete(data.id);
    clearTimeout(job.timer);
    warm = true;
    if (data.ok) job.resolve(data.result);
    else job.reject(new Error(data.error));
  };
  worker.onerror = (event) => {
    for (const [, job] of pending) job.reject(new Error(event.message || "Python worker failed."));
    pending.clear();
    worker = null;
    warm = false;
  };
}

export function isWarm() {
  return warm;
}

export function checkPython(checker, code, packages = []) {
  if (!worker) startWorker();
  const id = nextId++;
  const limit = warm ? RUN_TIMEOUT_MS : FIRST_LOAD_TIMEOUT_MS;
  return new Promise((resolve, reject) => {
    const wasWarm = warm;
    const timer = setTimeout(() => {
      pending.delete(id);
      worker?.terminate();
      worker = null;
      warm = false;
      reject(new Error(wasWarm
        ? "Your code ran for too long. Check for an endless loop."
        : "Python took too long to load. Check your connection and try again."));
    }, limit);
    pending.set(id, { resolve, reject, timer });
    worker.postMessage({ id, base: pyodideBase(), checker, code, packages });
  });
}
