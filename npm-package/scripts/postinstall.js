#!/usr/bin/env node
/**
 * postinstall.js — Runs after `npm install ktui`.
 * Checks that the platform binary was resolved; prints a friendly message
 * if the optional package is missing (e.g. unsupported platform).
 */
"use strict";

const os = require("os");

const SUPPORTED = ["linux-x64", "darwin-x64", "darwin-arm64", "win32-x64"];
const key = `${process.platform}-${os.arch()}`;

if (!SUPPORTED.includes(key)) {
  console.warn(`\nktui: ⚠  Pre-built binary not available for ${key}.`);
  console.warn("To build from source, see: https://github.com/marceleno1717/ktui#building\n");
}
