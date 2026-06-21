import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const root = process.cwd();
const windowsPython = join(root, "packages", "api", "venv", "Scripts", "python.exe");
const unixPython = join(root, "packages", "api", "venv", "bin", "python");
const python = existsSync(windowsPython)
  ? windowsPython
  : existsSync(unixPython)
    ? unixPython
    : process.platform === "win32"
      ? "python"
      : "python3";

const result = spawnSync(
  python,
  ["-m", "pytest", "packages/api/tests", ...process.argv.slice(2)],
  {
    cwd: root,
    env: { ...process.env, APP_ENV: process.env.APP_ENV ?? "test" },
    stdio: "inherit",
  },
);

if (result.error) {
  console.error(`Failed to start API tests with ${python}:`, result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
