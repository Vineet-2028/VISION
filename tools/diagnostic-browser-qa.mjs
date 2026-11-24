// Isolated, synthetic browser QA. Never reads a user's browser profile or footage.
// Setup: npm install --prefix .tools/browser-qa --save-exact playwright@1.65.1
// Then: .tools/browser-qa/node_modules/.bin/playwright install chromium
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { createHash, randomBytes } from "node:crypto";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { spawn, execFileSync } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";

const require = createRequire(import.meta.url);
const { chromium } = require("../.tools/browser-qa/node_modules/playwright");
const root = resolve("benchmark-results/final-closure-browser");
const caseRoot = resolve(root, "synthetic-case");
await mkdir(caseRoot, { recursive: true });
const secret = randomBytes(32).toString("hex");
const results = [];
const errors = [];
const consoleErrors = [];
let completed = false;
const browser = await chromium.launch({ headless: true });
let server;
let log = "";
const check = (name) => {
  results.push(name);
  console.log(`PASS ${name}`);
};
const index = {
  schema: "vision.field.case.v1",
  session_id: "SYNTHETIC_BROWSER_QA",
  frames: Array.from({ length: 3 }, (_, i) => ({
    index: i,
    sequence: i + 1,
    camera_ns: String(1000000000 + i * 250000000),
  })),
};
async function saveIndex(value = index) {
  await writeFile(resolve(caseRoot, "index.json"), JSON.stringify(value));
}
async function start(media, port) {
  log = "";
  server = spawn(
    process.execPath,
    [
      resolve("node_modules/next/dist/bin/next"),
      "dev",
      "--hostname",
      "127.0.0.1",
      "--port",
      String(port),
    ],
    {
      cwd: resolve("apps/web"),
      windowsHide: true,
      env: {
        ...process.env,
        NEXT_TELEMETRY_DISABLED: "1",
        VISION_LAB_SECRET: secret,
        VISION_DIAGNOSTIC_CASE: caseRoot,
        VISION_LAB_MEDIA_ENABLED: media,
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  server.stdout.on("data", (data) => {
    log += data;
  });
  server.stderr.on("data", (data) => {
    log += data;
  });
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 90; i++) {
    if (server.exitCode !== null) throw new Error("QA server exited");
    try {
      if (
        (
          await fetch(`${base}/lab/login`, {
            signal: AbortSignal.timeout(2000),
          })
        ).ok
      )
        return base;
    } catch {
      /* Startup only. */
    }
    await delay(500);
  }
  throw new Error("QA server startup timeout");
}
async function stop() {
  if (!server) return;
  if (server.exitCode === null) {
    if (process.platform === "win32")
      execFileSync(
        resolve(
          process.env.SystemRoot ?? "C:/Windows",
          "System32/taskkill.exe",
        ),
        ["/PID", String(server.pid), "/T", "/F"],
        { windowsHide: true, stdio: "ignore" },
      );
    else server.kill("SIGTERM");
  }
  await writeFile(resolve(root, "server.log"), log);
  server = undefined;
}
async function login(page, base) {
  await page.goto(`${base}/lab/login`);
  await page.getByLabel("Lab access secret").fill(secret);
  await page.getByRole("button", { name: "Unlock Lab" }).click();
  await page.waitForURL(`${base}/lab`);
}
async function evidence(page) {
  await page.locator("pre").filter({ hasText: "recorded_events" }).waitFor();
}
try {
  const generator = await browser.newPage();
  const jpeg = await generator.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const context = canvas.getContext("2d");
    context.fillStyle = "#234567";
    context.fillRect(0, 0, 320, 240);
    return canvas.toDataURL("image/jpeg").split(",")[1];
  });
  await generator.close();
  const bytes = Buffer.from(jpeg, "base64");
  for (const frame of index.frames) {
    await writeFile(resolve(caseRoot, `${frame.index}.jpg`), bytes);
    await writeFile(
      resolve(caseRoot, `${frame.index}.json`),
      JSON.stringify({
        ...frame,
        width: 320,
        height: 240,
        jpeg_sha256: createHash("sha256").update(bytes).digest("hex"),
        recorded_events: [
          {
            detector_diagnostics: {
              source_sequence: frame.sequence,
              source_id: index.session_id,
              accepted_samples: [
                {
                  original_box: [20, 20, 120, 120],
                  score: 0.9,
                  class_name: "FIXTURE",
                },
              ],
              rejected_samples: [
                {
                  original_box: [140, 30, 200, 100],
                  score: 0.1,
                  class_name: "FIXTURE",
                },
              ],
            },
            object_diagnostics: {
              objects: [
                {
                  entity_id: `fixture-${frame.index}`,
                  track_id: 1,
                  semantics: "UNKNOWN",
                  world_reasons: ["SYNTHETIC"],
                  risk: "UNKNOWN",
                  attention: "UNKNOWN",
                },
              ],
            },
          },
        ],
        feedback: [{ kind: "WRONG_NAME", provenance: "SYNTHETIC_TEST_ONLY" }],
      }),
    );
  }
  await saveIndex();
  await writeFile(
    resolve(caseRoot, "detector-replay.json"),
    JSON.stringify({
      schema: "vision.field.input-replay.v1",
      session_id: index.session_id,
      frames: index.frames.map((frame) => ({
        ...frame,
        jpeg_sha256: createHash("sha256").update(bytes).digest("hex"),
        recomputed_output: { scope: "SYNTHETIC_RECOMPUTATION_FIXTURE" },
      })),
      recomputation_provenance: { evidence: "SYNTHETIC_TEST_ONLY" },
    }),
  );
  let base = await start("1", 3187);
  const context = await browser.newContext();
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.goto(`${base}/lab/diagnostics`);
  await page.waitForURL(`${base}/lab/login`);
  assert.equal(
    (await context.request.get(`${base}/api/diagnostics`)).status(),
    401,
  );
  assert.equal(
    (
      await context.request.get(`${base}/api/diagnostics?frame=0&media=1`)
    ).status(),
    401,
  );
  check("anonymous page and media rejected");
  await page
    .getByLabel("Lab access secret")
    .fill("wrong-secret-that-is-at-least-32-characters");
  await page.getByRole("button", { name: "Unlock Lab" }).click();
  await page.getByText("Invalid credentials").waitFor();
  check("wrong secret rejected");
  await login(page, base);
  check("correct login");
  await page.goto(`${base}/lab/diagnostics`);
  await evidence(page);
  await page.locator("img").evaluate((img) => img.decode());
  assert.equal(
    await page
      .locator(
        'svg[aria-label="Candidate boxes in original image coordinates"] rect',
      )
      .count(),
    1,
  );
  await page.getByLabel("Rejected candidates").check();
  assert.equal(
    await page
      .locator(
        'svg[aria-label="Candidate boxes in original image coordinates"] rect',
      )
      .count(),
    2,
  );
  await page.getByLabel("Accepted candidates").uncheck();
  assert.equal(
    await page
      .locator(
        'svg[aria-label="Candidate boxes in original image coordinates"] rect',
      )
      .count(),
    1,
  );
  check("accepted/rejected image overlays");
  const text = await page.locator("pre").innerText();
  for (const field of [
    "track_id",
    "semantics",
    "world_reasons",
    "risk",
    "attention",
    "WRONG_NAME",
    "UNKNOWN",
    "recomputed_output",
    "SYNTHETIC_RECOMPUTATION_FIXTURE",
  ])
    assert.ok(text.includes(field), field);
  check("recorded stage evidence, markers and separate recomputation");
  await page.getByLabel("Entity evidence").selectOption("0");
  assert.ok((await page.locator("pre").innerText()).includes("fixture-0"));
  await page.getByRole("button", { name: "Next frame" }).click();
  await evidence(page);
  assert.equal(await page.getByLabel("Entity evidence").inputValue(), "-1");
  check("step resets entity identity selection");
  await page.getByRole("button", { name: "Previous frame" }).click();
  await evidence(page);
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  check("pause");
  await page.getByLabel("Capture position").focus();
  await page.keyboard.press("End");
  await page
    .getByText("Session SYNTHETIC_BROWSER_QA · Capture 3", { exact: true })
    .waitFor();
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await page.getByRole("button", { name: "Pause", exact: true }).waitFor();
  await page.getByRole("button", { name: "Play", exact: true }).waitFor();
  check("keyboard seek, replay and end-of-clip stop");
  await page.reload();
  await evidence(page);
  check("refresh retains authentication");
  await page.screenshot({ path: resolve(root, "desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  );
  await page.screenshot({ path: resolve(root, "mobile.png"), fullPage: true });
  check("mobile layout");
  const packetPath = resolve(caseRoot, "0.json");
  const originalPacket = await readFile(packetPath, "utf8");
  const packet = JSON.parse(originalPacket);
  const sourceEvent = structuredClone(packet.recorded_events[0]);
  packet.recorded_events[0].detector_diagnostics.source_sequence = 999;
  await writeFile(packetPath, JSON.stringify(packet));
  await page.reload();
  await evidence(page);
  assert.equal(
    await page
      .locator(
        'svg[aria-label="Candidate boxes in original image coordinates"] rect',
      )
      .count(),
    0,
  );
  sourceEvent.sequence = 9;
  packet.detector_source_events = [sourceEvent];
  await writeFile(packetPath, JSON.stringify(packet));
  await page.reload();
  await evidence(page);
  assert.equal(
    await page
      .locator(
        'svg[aria-label="Candidate boxes in original image coordinates"] rect',
      )
      .count(),
    1,
  );
  check(
    "older-source overlays rejected; exact-source later publications recovered",
  );
  packet.camera_ns = "101";
  await writeFile(packetPath, JSON.stringify(packet));
  await page.reload();
  await page.getByRole("alert").waitFor();
  check("corrupt frame identity rejected");
  await writeFile(packetPath, originalPacket);
  await page.reload();
  await evidence(page);
  await page.route("**/api/diagnostics?frame=1", (route) => route.abort());
  await page.getByRole("button", { name: "Next frame" }).click();
  await page.getByRole("alert").waitFor();
  await page.unroute("**/api/diagnostics?frame=1");
  await page.getByRole("button", { name: "Retry case" }).click();
  await evidence(page);
  check("disconnect and retry");
  await saveIndex({
    ...index,
    frames: [{ sequence: 1, camera_ns: "invalid" }],
  });
  await page.reload();
  await page.getByRole("alert").waitFor();
  check("corrupt index fails closed");
  await saveIndex({ ...index, frames: [] });
  await page.reload();
  await page.getByText("This case contains no captures.").waitFor();
  assert.equal(await page.getByLabel("Capture position").count(), 0);
  check("empty case");
  await saveIndex();
  await context.close();
  await stop();
  base = await start("0", 3188);
  const closed = await browser.newContext();
  const denied = await closed.newPage();
  denied.on("pageerror", (error) => errors.push(String(error)));
  await login(denied, base);
  await denied.goto(`${base}/lab/diagnostics`);
  await evidence(denied);
  await denied.getByText(/Image unavailable/).waitFor();
  assert.equal(
    (
      await closed.request.get(`${base}/api/diagnostics?frame=0&media=1`)
    ).status(),
    403,
  );
  await denied.screenshot({
    path: resolve(root, "media-disabled.png"),
    fullPage: true,
  });
  check("media opt-in gate and visible failure message");
  await closed.close();
  assert.deepEqual(errors, []);
  check("no uncaught browser errors");
  completed = true;
} catch (error) {
  console.error(error);
  throw error;
} finally {
  await stop();
  await browser.close();
  await writeFile(
    resolve(root, "results.json"),
    JSON.stringify(
      {
        synthetic: true,
        completed,
        passed: results,
        browserErrors: errors,
        consoleErrors,
      },
      null,
      2,
    ),
  );
  // Assert fixtures are synthetic rather than accepting an operator case path.
  assert.ok(
    (await readFile(resolve(caseRoot, "index.json"), "utf8")).includes(
      "SYNTHETIC_BROWSER_QA",
    ),
  );
}
