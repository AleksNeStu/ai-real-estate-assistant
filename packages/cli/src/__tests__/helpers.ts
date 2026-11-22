/**
 * What the tests share: where the package is, how a recorded answer is read
 * back, and how a local server is stood up in front of the client.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { createServer, type Server } from 'node:http';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/** The root of the package, found by walking up to the package.json. */
export function packageRoot(): string {
  let dir = dirname(fileURLToPath(import.meta.url));
  for (let step = 0; step < 8; step += 1) {
    try {
      readFileSync(resolve(dir, 'package.json'));
      return dir;
    } catch {
      dir = dirname(dir);
    }
  }
  throw new Error('The package root was not found.');
}

/** A recorded answer, read from the fixtures. */
export function fixture(name: string): unknown {
  return JSON.parse(readFileSync(resolve(packageRoot(), 'fixtures', name), 'utf8'));
}

/** The recorded answer as the server would send it. */
export function fixtureText(name: string): string {
  return JSON.stringify(fixture(name));
}

/** Every file of the package, except the installed dependencies. */
export function packageFiles(root = packageRoot()): string[] {
  const found: string[] = [];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir)) {
      if (entry === 'node_modules' || entry === '.git') continue;
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) walk(full);
      else found.push(full);
    }
  };
  walk(root);
  return found;
}

export interface RecordedRequest {
  method: string;
  url: string;
  headers: Record<string, string | string[] | undefined>;
  body: string;
}

/**
 * A server that answers every request with one recorded body and remembers
 * what it was asked.
 */
export async function startRecordingServer(
  body: string,
  status = 200,
): Promise<{
  url: string;
  requests: RecordedRequest[];
  close: () => Promise<void>;
  server: Server;
}> {
  const requests: RecordedRequest[] = [];
  const server = createServer((request, response) => {
    const chunks: Buffer[] = [];
    request.on('data', (chunk: Buffer) => chunks.push(chunk));
    request.on('end', () => {
      requests.push({
        method: request.method ?? '',
        url: request.url ?? '',
        headers: request.headers,
        body: Buffer.concat(chunks).toString('utf8'),
      });
      response.writeHead(status, { 'content-type': 'application/json' });
      response.end(body);
    });
  });

  await new Promise<void>((resolveListen) => server.listen(0, '127.0.0.1', resolveListen));
  const address = server.address();
  if (address === null || typeof address === 'string') {
    throw new Error('The recording server did not get an address.');
  }

  return {
    url: `http://127.0.0.1:${address.port}`,
    requests,
    close: () =>
      new Promise<void>((resolveClose, rejectClose) =>
        server.close((error) => (error ? rejectClose(error) : resolveClose())),
      ),
    server,
  };
}
