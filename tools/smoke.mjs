import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { copyFile, mkdtemp, unlink, rmdir } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const root = fileURLToPath(new URL("../", import.meta.url));
const scratch = await mkdtemp(join(tmpdir(), "sentinel-smoke-"));
const jar = join(scratch, "sentinel-api.jar");
const children = [];

async function freePort() {
  const server = createServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const port = server.address().port;
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
  return port;
}

function launch(command, args, cwd, environment = {}) {
  const child = spawn(command, args, {
    cwd,
    windowsHide: true,
    env: { ...process.env, ...environment, NEXT_TELEMETRY_DISABLED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  const state = { child, output: "", exited: false, error: null };
  state.closed = new Promise((resolve) =>
    child.once("close", () => {
      state.exited = true;
      resolve();
    }),
  );
  child.once("error", (error) => {
    state.error = error;
  });
  for (const stream of [child.stdout, child.stderr]) {
    stream.on("data", (data) => {
      state.output = (state.output + data).slice(-12000);
    });
  }
  children.push(state);
  return state;
}

async function waitUntilReady(state, marker) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (state.error || state.exited)
      throw new Error(`Test process failed: ${state.error ?? state.output}`);
    if (marker.test(state.output)) return;
    await delay(100);
  }
  throw new Error(`Test startup timed out: ${state.output}`);
}

async function stop(state) {
  if (state.exited) return;
  state.child.kill();
  await Promise.race([state.closed, delay(5000, undefined, { ref: false })]);
  if (!state.exited) {
    state.child.kill("SIGKILL");
    await state.closed;
  }
}

async function get(url) {
  const response = await fetch(url, { signal: AbortSignal.timeout(5000) });
  const body = await response.text();
  assert.equal(response.status, 200, `${url}: unexpected HTTP status`);
  return body;
}

try {
  // Never run the build output directly: rebuilding a running JAR locks it on Windows.
  await copyFile(join(root, "apps/api/target/sentinel-api-0.1.0.jar"), jar);
  const java = process.env.JAVA_HOME
    ? join(
        process.env.JAVA_HOME,
        "bin",
        process.platform === "win32" ? "java.exe" : "java",
      )
    : "java";
  const api = launch(
    java,
    ["-jar", jar, "--server.port=0", "--server.address=127.0.0.1"],
    root,
  );
  await waitUntilReady(api, /Tomcat started on port (\d+)/);
  const apiPort = api.output.match(/Tomcat started on port (\d+)/)[1];
  const apiUrl = `http://127.0.0.1:${apiPort}`;
  for (const route of ["live", "ready"]) {
    assert.deepEqual(JSON.parse(await get(`${apiUrl}/health/${route}`)), {
      status: "ok",
      service: "sentinel-api",
    });
  }
  const webPort = await freePort();
  const web = launch(
    process.execPath,
    [
      "scripts/next.mjs",
      "start",
      "--hostname",
      "127.0.0.1",
      "--port",
      String(webPort),
    ],
    join(root, "apps/web"),
    { API_BASE_URL: apiUrl },
  );
  await waitUntilReady(web, /Ready in/);
  const webUrl = `http://127.0.0.1:${webPort}`;
  assert.match(await get(webUrl), /Guardian Disabled/);
  const pages = await Promise.all(
    Array.from({ length: 8 }, () => get(`${webUrl}/health`)),
  );
  for (const page of pages) assert.match(page, /<dd>Healthy<\/dd>/);
  await stop(api);
  assert.match(await get(`${webUrl}/health`), /<dd>Unavailable<\/dd>/);
  console.log(
    "PASS: API contracts, production home, 8 concurrent health requests, and API outage handling.",
  );
} finally {
  await Promise.all(children.map(stop));
  await unlink(jar).catch((error) => {
    if (error.code !== "ENOENT") throw error;
  });
  await rmdir(scratch);
}
