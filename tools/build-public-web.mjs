// Static distribution uses an allowlist, never a conditional hide of Lab routes.
import {
  mkdir,
  readFile,
  writeFile,
  cp,
  rm,
  lstat,
  readdir,
} from "node:fs/promises";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
const root = fileURLToPath(new URL("../", import.meta.url));
const stage = resolve(root, "dist", "public-web-source");
try {
  if ((await lstat(resolve(root, "dist"))).isSymbolicLink())
    throw Error("Distribution directory must not be a symlink");
} catch (e) {
  if (e.code !== "ENOENT") throw e;
}
if (stage !== resolve(root, "dist/public-web-source"))
  throw Error("Unsafe build path");
try {
  if ((await lstat(stage)).isSymbolicLink())
    throw Error("Build path must not be a symlink");
  await rm(stage, { recursive: true });
} catch (e) {
  if (e.code !== "ENOENT") throw e;
}
await mkdir(join(stage, "src/app"), { recursive: true });
const pages = [
  "demo",
  "how-it-works",
  "privacy",
  "limitations",
  "technology",
  "research",
  "get-vision",
];
for (const file of [
  "page.tsx",
  "layout.tsx",
  "globals.css",
  ...pages.map((p) => `${p}/page.tsx`),
]) {
  const to = join(stage, "src/app", file);
  await mkdir(resolve(to, ".."), { recursive: true });
  const source = await readFile(join(root, "apps/web/src/app", file), "utf8");
  // Plain navigation avoids host-specific RSC prefetch rewrites on generic CDNs.
  await writeFile(
    to,
    source.replaceAll('from "next/link"', 'from "@/components/public-link"'),
  );
}
await mkdir(join(stage, "src/components"));
await writeFile(
  join(stage, "src/components/public-link.tsx"),
  `import type { AnchorHTMLAttributes } from "react";
export default function PublicLink(props: AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <a {...props} />;
}
`,
);
await cp(
  join(root, "apps/web/src/components/product-demo.tsx"),
  join(stage, "src/components/product-demo.tsx"),
);
const tsconfig = JSON.parse(
  await readFile(join(root, "apps/web/tsconfig.json"), "utf8"),
);
tsconfig.compilerOptions.paths = { "@/*": ["./src/*"] };
await writeFile(join(stage, "tsconfig.json"), JSON.stringify(tsconfig));
const pkg = JSON.parse(
  await readFile(join(root, "apps/web/package.json"), "utf8"),
);
await writeFile(
  join(stage, "package.json"),
  JSON.stringify({ ...pkg, name: "vision-public-build" }),
);
await writeFile(
  join(stage, "next.config.mjs"),
  'export default {output:"export",trailingSlash:true};\n',
);
const result = spawnSync(
  process.execPath,
  [join(root, "node_modules/next/dist/bin/next"), "build", stage],
  {
    cwd: root,
    stdio: "inherit",
    env: { ...process.env, NEXT_TELEMETRY_DISABLED: "1" },
  },
);
if (result.status !== 0) process.exit(result.status ?? 1);
async function assertPublicFiles(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isSymbolicLink()) throw Error("Linked asset in public export");
    if (entry.isDirectory()) await assertPublicFiles(path);
    else {
      if (/\.(mp4|mov|webm|onnx|pt|sqlite|db|pem|env)$/i.test(entry.name))
        throw Error(`Private asset type in export: ${entry.name}`);
      if (/\.(html|js|json|txt)$/.test(entry.name)) {
        const text = await readFile(path, "utf8");
        if (/\/api\/replay\/|VISION_LAB_SECRET|VISION_PAIR_V1/.test(text))
          throw Error(`Private interface in public export: ${entry.name}`);
      }
    }
  }
}
await assertPublicFiles(join(stage, "out"));
await writeFile(
  join(stage, "out", "_headers"),
  `/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
`,
);
for (const forbidden of [
  "lab",
  "api",
  "live",
  "session",
  "review",
  "metrics",
]) {
  try {
    await lstat(join(stage, "out", forbidden));
    throw Error(`Private route in static export: ${forbidden}`);
  } catch (e) {
    if (e.code !== "ENOENT") throw e;
  }
}
console.log(`Public static output verified: ${join(stage, "out")}`);
