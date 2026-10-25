/* In-browser, real Python WebAssembly worker.
 * Pinned CDN artifact: Pyodide 0.27.7 (CPython 3.12.7).
 * No DOM, no OS shell, no access to the host Vercel filesystem.
 * Parent kills the worker if the runtime exceeds its execution time.
 */
let pyodide = null;
let loading = null;
const INDEX = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";

async function getRuntime() {
  if (pyodide) return pyodide;
  if (loading) return loading;
  postMessage({type: "loading"});
  loading = (async () => {
    importScripts(INDEX + "pyodide.js");
    const runtime = await loadPyodide({indexURL: INDEX});
    runtime.setStdout({batched: text => postMessage({type: "stdout", text})});
    runtime.setStderr({batched: text => postMessage({type: "stderr", text})});
    pyodide = runtime;
    return runtime;
  })();
  try {
    return await loading;
  } catch (error) {
    loading = null;
    throw error;
  }
}

self.onmessage = async event => {
  const payload = event.data || {};
  if (payload.type !== "run") return;
  if (typeof payload.code !== "string" || payload.code.length > 8000) {
    postMessage({type: "done", ok: false, error: "Invalid code length (max 8,000 characters)."});
    return;
  }
  try {
    const engine = await getRuntime();
    const version = engine.runPython("import sys; sys.version.split()[0]");
    postMessage({type: "ready", version: String(version)});
    let result;
    try {
      result = await engine.runPythonAsync(payload.code);
      if (result !== undefined && result !== null) {
        postMessage({type: "result", value: String(result).slice(0, 1500)});
      }
      postMessage({type: "done", ok: true});
    } catch (pythonError) {
      postMessage({type: "done", ok: false, error: String(pythonError).slice(0, 4000)});
    } finally {
      if (result && typeof result.destroy === "function") result.destroy();
    }
  } catch (error) {
    postMessage({type: "fatal", error: String(error).slice(0, 1200)});
  }
};
