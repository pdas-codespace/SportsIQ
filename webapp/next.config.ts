import type { NextConfig } from "next";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

// Force-load webapp .env.local so its values override inherited process env
// vars (e.g., SPORTS_IQ_SPORT from the repo-root .env leaking via VS Code
// or shell profile into the Node process).
const envLocal = resolve(__dirname, ".env.local");
if (existsSync(envLocal)) {
  for (const line of readFileSync(envLocal, "utf8").split("\n")) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (m && !line.trimStart().startsWith("#")) {
      process.env[m[1]] = m[2];
    }
  }
}

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: __dirname,   // fix: Turbopack was picking up wrong workspace root
  },
};

export default nextConfig;
