import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

// Set before Next loads, for development, type generation, builds, and serving.
process.env.NEXT_TELEMETRY_DISABLED = "1";
const require = createRequire(import.meta.url);
await import(pathToFileURL(require.resolve("next/dist/bin/next")).href);
