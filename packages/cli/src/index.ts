#!/usr/bin/env node
/**
 * The bin. Everything else lives in `cli.ts`, which is what the tests drive.
 */

import { main } from './cli.js';

process.exitCode = await main(process.argv.slice(2));
