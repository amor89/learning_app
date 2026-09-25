// Module Web Worker that loads Pyodide and the checker package, then runs checks.
// Pyodide 314 supports module workers only.
// Messages in:  { id, base, checker, code, packages }
// Messages out: { id, ok: true, result } or { id, ok: false, error }

let pyodideReady = null;
const loadedPackages = new Set();

async function boot(base) {
  const { loadPyodide } = await import(`${base}pyodide.mjs`);
  const pyodide = await loadPyodide({ indexURL: base });
  const pyRoot = new URL("../py/", self.location.href);
  const manifest = await (await fetch(new URL("manifest.json", pyRoot))).json();
  pyodide.FS.mkdirTree("/home/pyodide/checkers");
  for (const name of manifest.checkers) {
    const source = await (await fetch(new URL(`checkers/${name}`, pyRoot))).text();
    pyodide.FS.writeFile(`/home/pyodide/checkers/${name}`, source);
  }
  pyodide.runPython("import sys\nif '/home/pyodide' not in sys.path: sys.path.insert(0, '/home/pyodide')");
  return pyodide;
}

self.onmessage = async (event) => {
  const { id, base, checker, code, packages } = event.data;
  try {
    pyodideReady ??= boot(base);
    const pyodide = await pyodideReady;
    const wanted = (packages ?? []).filter((p) => !loadedPackages.has(p));
    if (wanted.length) {
      await pyodide.loadPackage(wanted);
      wanted.forEach((p) => loadedPackages.add(p));
    }
    const run = pyodide.runPython("from checkers import check_python_json\ncheck_python_json");
    const result = JSON.parse(run(JSON.stringify(checker), code));
    run.destroy();
    self.postMessage({ id, ok: true, result });
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error?.message ?? error) });
  }
};
