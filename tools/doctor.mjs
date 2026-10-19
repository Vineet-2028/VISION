import { spawnSync } from "node:child_process";
import { join } from "node:path";

const [major, minor] = process.versions.node.split(".").map(Number);
if (major !== 22 || minor < 21) {
  throw new Error("Use Node 22.21.0 or newer within Node 22.");
}
const npmVersion =
  process.env.npm_config_user_agent?.match(/npm\/(\d+)\./)?.[1];
if (npmVersion !== "10") throw new Error("Run npm run doctor using npm 10.");
const java = process.env.JAVA_HOME
  ? join(
      process.env.JAVA_HOME,
      "bin",
      process.platform === "win32" ? "java.exe" : "java",
    )
  : "java";
const result = spawnSync(java, ["-version"], {
  encoding: "utf8",
  windowsHide: true,
});
if (
  result.error ||
  result.status !== 0 ||
  !/version "21[.\"]/.test(result.stderr)
) {
  throw new Error("Install JDK 21 and set JAVA_HOME to its directory.");
}
console.log(
  `Ready: Node ${process.versions.node}, npm 10, JDK 21. Docker is optional.`,
);
