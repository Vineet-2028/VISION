import { mkdtemp, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, test } from "vitest";
import { replayStream } from "./replay-store";

const directories: string[] = [];
afterEach(async () => {
  for (const directory of directories.splice(0))
    await rm(directory, { recursive: true, force: true });
});
async function fixture() {
  const directory = await mkdtemp(join(tmpdir(), "vision-video-"));
  directories.push(directory);
  const path = join(directory, "fixture.bin");
  const bytes = Buffer.alloc(200_000, 42);
  bytes[77] = 9;
  await writeFile(path, bytes);
  const info = await stat(path);
  return { path, size: info.size, mtimeMs: info.mtimeMs, ino: info.ino };
}
test("video range returns exactly the requested bytes", async () => {
  const file = await fixture();
  const stream = await replayStream(file, 77, 80);
  expect([...new Uint8Array(await new Response(stream).arrayBuffer())]).toEqual(
    [9, 42, 42, 42],
  );
});
test("cancelling during a pending read closes without a second controller operation", async () => {
  const file = await fixture();
  for (let i = 0; i < 20; i++) {
    const reader = (await replayStream(file, 0, file.size - 1)).getReader();
    const read = reader.read();
    await reader.cancel();
    expect((await read).done).toBe(true);
  }
});
