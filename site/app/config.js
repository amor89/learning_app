// Runtime settings. Pinned versions live in VERSIONS.md.
export const PYODIDE_VERSION = "314.0.7";
export const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

// Tests and offline development override the Pyodide location with ?pyodide=<url>.
export function pyodideBase() {
  const override = new URLSearchParams(location.search).get("pyodide");
  return override ? new URL(override, location.href).href : PYODIDE_CDN;
}

export const FIRST_LOAD_TIMEOUT_MS = 120_000;
export const RUN_TIMEOUT_MS = 15_000;
