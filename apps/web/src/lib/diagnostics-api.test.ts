import { expect, test } from "vitest";
import { GET } from "../app/api/diagnostics/route";
import { issueLabSession } from "./lab-auth";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash } from "node:crypto";

test("media needs separate consent and rejects a tampered capture", async () => {
  const root = await mkdtemp(join(tmpdir(), "vision-diagnostic-test-"));
  const original = {
    secret: process.env.VISION_LAB_SECRET,
    directory: process.env.VISION_DIAGNOSTIC_CASE,
    media: process.env.VISION_LAB_MEDIA_ENABLED,
  };
  const bytes = Buffer.from([255, 216, 255, 217]);
  try {
    process.env.VISION_LAB_SECRET = "diagnostic-test-secret-32-characters";
    process.env.VISION_DIAGNOSTIC_CASE = root;
    process.env.VISION_LAB_MEDIA_ENABLED = "0";
    await writeFile(
      join(root, "index.json"),
      JSON.stringify({
        schema: "vision.field.case.v1",
        session_id: "fixture",
        frames: [{ sequence: 7, camera_ns: "100" }],
      }),
    );
    await writeFile(
      join(root, "0.json"),
      JSON.stringify({
        sequence: 7,
        camera_ns: "100",
        width: 2,
        height: 2,
        recorded_events: [],
        jpeg_sha256: createHash("sha256").update(bytes).digest("hex"),
      }),
    );
    await writeFile(join(root, "0.jpg"), bytes);
    const request = () =>
      new Request("http://localhost/api/diagnostics?frame=0&media=1", {
        headers: {
          cookie: `vision_lab=${issueLabSession(process.env.VISION_LAB_SECRET!)}`,
        },
      });
    expect((await GET(request())).status).toBe(403);
    process.env.VISION_LAB_MEDIA_ENABLED = "1";
    const allowed = await GET(request());
    expect(allowed.status).toBe(200);
    expect(Buffer.from(await allowed.arrayBuffer())).toEqual(bytes);
    const recordedRequest = () =>
      new Request("http://localhost/api/diagnostics?frame=0", {
        headers: {
          cookie: `vision_lab=${issueLabSession(process.env.VISION_LAB_SECRET!)}`,
        },
      });
    const recomputed = {
      schema: "vision.field.input-replay.v1",
      session_id: "fixture",
      frames: [
        {
          sequence: 7,
          camera_ns: "100",
          jpeg_sha256: createHash("sha256").update(bytes).digest("hex"),
          recomputed_output: { scope: "TEST_FIXTURE" },
        },
      ],
    };
    await writeFile(
      join(root, "detector-replay.json"),
      JSON.stringify(recomputed),
    );
    expect(
      (await (await GET(recordedRequest())).json()).recomputed_output.scope,
    ).toBe("TEST_FIXTURE");
    recomputed.frames[0]!.camera_ns = "101";
    await writeFile(
      join(root, "detector-replay.json"),
      JSON.stringify(recomputed),
    );
    expect((await GET(recordedRequest())).status).toBe(422);
    await writeFile(join(root, "0.jpg"), Buffer.from("modified"));
    expect((await GET(request())).status).toBe(422);
  } finally {
    for (const [name, value] of Object.entries({
      VISION_LAB_SECRET: original.secret,
      VISION_DIAGNOSTIC_CASE: original.directory,
      VISION_LAB_MEDIA_ENABLED: original.media,
    })) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
    await rm(root, { recursive: true, force: true });
  }
});

test("diagnostic media rejects anonymous requests", async () => {
  const response = await GET(
    new Request("http://localhost/api/diagnostics?frame=0&media=1"),
  );
  expect(response.status).toBe(401);
  expect(response.headers.get("cache-control")).toBe("no-store");
});

test("authenticated diagnostic access rejects nonlocal hosts", async () => {
  const previous = process.env.VISION_LAB_SECRET;
  process.env.VISION_LAB_SECRET = "diagnostic-test-secret-32-characters";
  try {
    const token = issueLabSession(process.env.VISION_LAB_SECRET);
    const response = await GET(
      new Request("https://example.com/api/diagnostics", {
        headers: { cookie: `vision_lab=${token}` },
      }),
    );
    expect(response.status).toBe(403);
  } finally {
    if (previous === undefined) delete process.env.VISION_LAB_SECRET;
    else process.env.VISION_LAB_SECRET = previous;
  }
});

test.each([
  [{ sequence: 0, camera_ns: "not-a-clock" }],
  [{ camera_ns: "100" }],
  [
    { sequence: 1, camera_ns: "100" },
    { sequence: 2, camera_ns: "99" },
  ],
  [null],
])(
  "rejects malformed or nonmonotonic case identities %j",
  async (...frames) => {
    const root = await mkdtemp(join(tmpdir(), "vision-invalid-case-"));
    const originalSecret = process.env.VISION_LAB_SECRET;
    const originalRoot = process.env.VISION_DIAGNOSTIC_CASE;
    process.env.VISION_LAB_SECRET =
      "synthetic-test-secret-at-least-32-characters";
    process.env.VISION_DIAGNOSTIC_CASE = root;
    try {
      await writeFile(
        join(root, "index.json"),
        JSON.stringify({
          schema: "vision.field.case.v1",
          session_id: "fixture",
          frames,
        }),
      );
      const response = await GET(
        new Request("http://localhost/api/diagnostics", {
          headers: {
            cookie: `vision_lab=${issueLabSession(process.env.VISION_LAB_SECRET)}`,
          },
        }),
      );
      expect(response.status).toBe(422);
    } finally {
      if (originalSecret === undefined) delete process.env.VISION_LAB_SECRET;
      else process.env.VISION_LAB_SECRET = originalSecret;
      if (originalRoot === undefined) delete process.env.VISION_DIAGNOSTIC_CASE;
      else process.env.VISION_DIAGNOSTIC_CASE = originalRoot;
      await rm(root, { recursive: true, force: true });
    }
  },
);
