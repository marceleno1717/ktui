#!/usr/bin/env node
/**
 * ktui launcher — detects the current platform, resolves the correct
 * pre-built binary from the optional platform package, and spawns it.
 */
"use strict";

const { spawnSync } = require("child_process");
const path = require("path");
const fs   = require("fs");
const os   = require("os");

// Map Node's process.platform + arch to our package names
const PLATFORM_MAP = {
  "linux-x64": "@ktui/linux-x64",
};

const key = `${process.platform}-${os.arch()}`;
const pkg = PLATFORM_MAP[key];

if (!pkg) {
  console.error(`ktui: unsupported platform: ${key}`);
  console.error("Supported platform: linux-x64");
  process.exit(1);
}

// Try to resolve the platform binary package
let binPath;
try {
  // Resolve binary inside the optional platform package
  const pkgDir = path.dirname(require.resolve(`${pkg}/package.json`));
  const binName = process.platform === "win32" ? "ktui.exe" : "ktui";
  binPath = path.join(pkgDir, "bin", binName);
} catch {
  console.error(`ktui: platform package ${pkg} is not installed.`);
  console.error("Try reinstalling: npm install -g @ktui/editor");
  process.exit(1);
}

if (!fs.existsSync(binPath)) {
  console.error(`ktui: binary not found at ${binPath}`);
  process.exit(1);
}

// Ensure executable on Unix
if (process.platform !== "win32") {
  fs.chmodSync(binPath, 0o755);
}

// Spawn the binary, forwarding all args and stdio
const result = spawnSync(binPath, process.argv.slice(2), {
  stdio: "inherit",
  env: process.env,
});

process.exit(result.status ?? 1);
