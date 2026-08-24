import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

/** Runs `make seed`'s underlying command against the running stack and
 * captures the printed session cookie so tests can authenticate as the
 * seeded recruiter without a real Google OAuth round trip (TS-06/R-13). */
export default function globalSetup(): void {
  const repoRoot = path.resolve(__dirname, "..");
  const output = execFileSync(
    "docker",
    ["compose", "exec", "-T", "api", "python", "-m", "app.scripts.seed"],
    { cwd: repoRoot, encoding: "utf-8" },
  );

  const match = output.match(/session cookie value: (\S+)/);
  if (!match) {
    throw new Error(`db:seed output didn't contain a session cookie:\n${output}`);
  }

  const authDir = path.resolve(__dirname, ".auth");
  mkdirSync(authDir, { recursive: true });
  writeFileSync(
    path.join(authDir, "session.json"),
    JSON.stringify({ sessionCookie: match[1] }),
  );
}
