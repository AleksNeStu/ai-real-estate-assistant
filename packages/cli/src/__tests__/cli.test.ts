/**
 * The command, run as a command.
 *
 * The bin is started as a process, with the address and the key in the
 * environment, and it is read the way a person reads it.
 */

import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it } from 'node:test';

import { fixtureText, packageFiles, packageRoot, startRecordingServer } from './helpers.js';

const ROOT = packageRoot();
const BIN = resolve(ROOT, 'dist', 'index.js');

interface RunResult {
  code: number | null;
  stdout: string;
  stderr: string;
}

function runBin(args: string[], env: Record<string, string>): Promise<RunResult> {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn(process.execPath, [BIN, ...args], {
      env: { ...process.env, ...env },
      cwd: ROOT,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString('utf8');
    });
    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString('utf8');
    });
    child.on('error', rejectRun);
    child.on('close', (code) => resolveRun({ code, stdout, stderr }));
  });
}

describe('the command', () => {
  it('values an address, with the address and the key taken from the environment', async () => {
    const server = await startRecordingServer(fixtureText('valuation.response.json'));
    const key = `pv-key-${Date.now()}-never-written-down`;
    try {
      const result = await runBin(
        ['valuation', '--city', 'Kraków', '--street', 'Myśliwska', '--area', '60', '--rooms', '3'],
        {
          PROPVECTOR_API_URL: `${server.url}/api/v1`,
          PROPVECTOR_API_KEY: key,
        },
      );

      assert.equal(result.code, 0, result.stderr);
      assert.match(result.stdout, /estimated value\s+959,182 PLN/);
      assert.match(result.stdout, /comparison area\s+Kraków, Śródmieście/);
      assert.match(result.stdout, /Myśliwska 68C/);

      assert.equal(server.requests.length, 1);
      const request = server.requests[0];
      assert.equal(request?.method, 'POST');
      assert.equal(request?.url, '/api/v1/tools/valuation');
      assert.equal(request?.headers['x-api-key'], key);
      assert.deepEqual(JSON.parse(request?.body ?? '{}'), {
        city: 'Kraków',
        street: 'Myśliwska',
        area_sqm: 60,
        rooms: 3,
      });
    } finally {
      await server.close();
    }
  });

  it('never writes the key down', async () => {
    const server = await startRecordingServer(fixtureText('chat.response.json'));
    const key = `pv-secret-${Date.now()}-never-written-down`;
    try {
      const result = await runBin(['chat', 'what does a flat in Krakow cost'], {
        PROPVECTOR_API_URL: `${server.url}/api/v1`,
        PROPVECTOR_API_KEY: key,
      });

      assert.equal(result.code, 0, result.stderr);
      assert.equal(result.stdout.includes(key), false);
      assert.equal(result.stderr.includes(key), false);

      for (const file of packageFiles(ROOT)) {
        const content = readFileSync(file, 'utf8');
        assert.equal(
          content.includes(key),
          false,
          `the key was found in ${file}`,
        );
      }
    } finally {
      await server.close();
    }
  });

  it('searches the catalogue', async () => {
    const server = await startRecordingServer(fixtureText('search.response.json'));
    try {
      const result = await runBin(['search', 'flats in Krakow', '--limit', '2'], {
        PROPVECTOR_API_URL: `${server.url}/api/v1`,
        PROPVECTOR_API_KEY: 'pv-key-for-the-search', // pragma: allowlist secret - a fake key for the test, not a credential
      });

      assert.equal(result.code, 0, result.stderr);
      assert.match(result.stdout, /results\s+2/);
      assert.match(result.stdout, /Myśliwska 68C, Kraków - 850,000 PLN - 60 m2/);
      assert.equal(server.requests[0]?.url, '/api/v1/search');
    } finally {
      await server.close();
    }
  });

  it('refuses a key passed as an argument', async () => {
    const result = await runBin(['search', 'flats', '--api-key', 'secret'], {
      PROPVECTOR_API_URL: 'http://127.0.0.1:1/api/v1',
      PROPVECTOR_API_KEY: 'pv-key-for-the-refusal', // pragma: allowlist secret - a fake key for the test, not a credential
    });

    assert.equal(result.code, 2);
    assert.match(result.stderr, /PROPVECTOR_API_KEY/);
  });

  it('says which variable is missing when the environment does not carry the key', async () => {
    const result = await runBin(['search', 'flats'], {
      PROPVECTOR_API_URL: 'http://127.0.0.1:1/api/v1',
      PROPVECTOR_API_KEY: '',
    });

    assert.equal(result.code, 2);
    assert.match(result.stderr, /PROPVECTOR_API_KEY/);
  });

  it('prints the usage when there is nothing to do', async () => {
    const result = await runBin([], {});
    assert.equal(result.code, 2);
    assert.match(result.stdout, /propvector valuation/);
    assert.match(result.stdout, /PROPVECTOR_API_URL/);
  });
});
