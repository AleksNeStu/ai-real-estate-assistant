#!/usr/bin/env node
/**
 * The test runner.
 *
 * `node --test` changed what a path means between the Node versions this
 * package supports - a directory in Node 20, a glob in Node 22 and later. The
 * package supports both, so the files are collected here and handed over
 * explicitly.
 */

import { spawnSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const directory = resolve(root, 'dist', '__tests__');

let entries = [];
try {
  entries = readdirSync(directory);
} catch {
  console.error(`The tests were not built: ${directory} does not exist. Run: npm run build`);
  process.exit(1);
}

const files = entries
  .filter((entry) => entry.endsWith('.test.js'))
  .sort()
  .map((entry) => join(directory, entry));

if (!files.length) {
  console.error(`No test files in ${directory}.`);
  process.exit(1);
}

const result = spawnSync(process.execPath, ['--test', ...files], { stdio: 'inherit' });
process.exit(result.status ?? 1);
