import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * The service worker the application ships.
 *
 * The worker is a plain file in `public/`, served as it is - there is no
 * browser in the test environment to run it in, so the contract it has to
 * keep is read out of the file itself.
 *
 * The contract is the update: a new version waits until the visitor accepts
 * it. A worker that takes over on its own would replace the page under the
 * reader, and the notice the application shows would be a lie.
 */

const WORKER = readFileSync(join(process.cwd(), 'public', 'sw.js'), 'utf-8');

/** The body of one event handler of the worker. */
function handler(event: string): string {
  const start = WORKER.indexOf(`addEventListener('${event}'`);
  expect(start).toBeGreaterThan(-1);
  const end = WORKER.indexOf("addEventListener('", start + 1);
  return WORKER.slice(start, end === -1 ? WORKER.length : end);
}

describe('the shipped service worker', () => {
  it('does not take over on install', () => {
    expect(handler('install')).not.toContain('skipWaiting');
  });

  it('takes over when the visitor accepts the update', () => {
    const messages = handler('message');

    expect(messages).toContain("event.data.type === 'SKIP_WAITING'");
    expect(messages).toContain('self.skipWaiting()');
  });

  it('precaches the shell of the app', () => {
    // The root of the site is a redirect into a language, and a redirect is
    // not a document that can be cached - the languages themselves are the
    // shell.
    expect(WORKER).toContain("'/en'");
    expect(WORKER).toContain("'/pl'");
  });

  it('serves the last page it saw when the connection is gone', () => {
    const navigation = handler('fetch');

    expect(navigation).toContain('networkFirstWithOfflineFallback');
  });
});
