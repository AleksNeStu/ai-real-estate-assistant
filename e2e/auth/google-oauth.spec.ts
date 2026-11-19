/**
 * The Google sign-in, driven end to end.
 *
 * WHAT IS UNDER TEST
 *
 * This repository's own OAuth wiring, in the browser: the button that appears
 * when the deployment says Google is configured, the redirect the click
 * builds towards the provider, the provider's answer coming back to the
 * callback route, and the session that route leaves behind.
 *
 * WHAT IS STUBBED, AND WHERE
 *
 * The identity provider, and only the identity provider. Its authorization
 * page and its answer are replaced at the network boundary - the browser
 * never leaves the machine - because a real Google round trip needs a test
 * identity, a client and a human at the consent screen. That is the
 * operator's gate, not this suite's.
 *
 * The start endpoint and the callback route are answered at the API boundary,
 * the way the rest of this suite answers the API. The callback's answer is
 * the session the backend sets once the provider's answer has been verified,
 * so the only thing that is faked about it is the provider's answer itself.
 * The backend's own start and callback logic is covered by its unit tests
 * (apps/api/tests/unit/test_auth_jwt_router.py).
 *
 * WHERE THE VALUES COME FROM
 *
 * The client id and the redirect URI are read from the configuration the
 * repository declares (`.env.example`), the provider's endpoint and its
 * scopes from the provider module that builds the authorization URL, and the
 * callback route from the application that serves it. The spec carries no
 * second copy of any of them, so a change in the configuration is a change
 * in what the spec asserts.
 *
 * THE SPEC BITES
 *
 * The flow only completes when the provider sends the visitor back to the
 * route the application owns. A redirect URI that points anywhere else leaves
 * the visitor signed out - which the second case asserts, and which is why
 * the first case can fail.
 */

import { test, expect, type Page } from '@playwright/test';
import { existsSync, readFileSync } from 'node:fs';
import { join, resolve, sep } from 'node:path';

const REPO_ROOT = resolve(__dirname, '..', '..');
const API_DIR = join(REPO_ROOT, 'apps/api');
const WEB_DIR = join(REPO_ROOT, 'apps/web');

/** The sign-in page, under one of the locales the application declares. */
const LOGIN_PATH = '/en/auth/login';

/**
 * The settings a file declares.
 *
 * A declaration in the example file is commented out - it is a template, not
 * an active setting - and it still says what the value looks like, so it is
 * read as well.
 */
function declaredSettings(file: string): Record<string, string> {
  const settings: Record<string, string> = {};
  for (const line of readFileSync(file, 'utf8').split(/\r?\n/)) {
    const match = /^\s*#?\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/.exec(line);
    if (!match) continue;
    const value = match[2].trim().replace(/^["'](.*)["']$/, '$1');
    if (value) settings[match[1]] = value;
  }
  return settings;
}

/**
 * The file the application is configured by.
 *
 * The repository's own declaration (`.env.example`) is the default: it is
 * committed, it holds no secret, and it says the same thing everywhere, so
 * the spec behaves the same on a workstation and on a runner. A deployment's
 * own `.env` is not read - the spec would then carry a deployment's values
 * and fail on a runner that has none.
 *
 * `OAUTH_CONFIG_FILE` points the spec at another configuration file. It is
 * how the "the spec bites" case is proven: a file that declares a redirect
 * URI the application does not own makes the sign-in fail.
 */
function configurationFile(): string {
  const override = process.env.OAUTH_CONFIG_FILE;
  if (override) return resolve(REPO_ROOT, override);
  return join(REPO_ROOT, '.env.example');
}

/** The provider's own configuration, read from the module that builds the URL. */
function providerConfiguration(): { authUrl: string; scopes: string[] } {
  const file = join(API_DIR, 'core/oauth/google.py');
  const source = readFileSync(file, 'utf8');
  const authUrl = /GOOGLE_AUTH_URL\s*=\s*"([^"]+)"/.exec(source)?.[1];
  const block = /DEFAULT_SCOPES\s*=\s*\[([\s\S]*?)\]/.exec(source)?.[1] ?? '';
  const scopes = [...block.matchAll(/"([^"]+)"/g)].map((match) => match[1]);
  if (!authUrl || scopes.length === 0) {
    throw new Error(`The Google provider's configuration could not be read from ${file}`);
  }
  return { authUrl, scopes };
}

/**
 * The route the provider sends the visitor back to: the API base the
 * frontend calls, plus the backend's OAuth callback route. Both are read
 * from the application, so the spec never carries a copy of a path the
 * application can move.
 */
function apiCallbackRoute(): string {
  const client = readFileSync(join(WEB_DIR, 'src/lib/auth.ts'), 'utf8');
  const apiBase = /NEXT_PUBLIC_API_URL\s*\|\|\s*'([^']+)'/.exec(client)?.[1];
  const router = readFileSync(join(API_DIR, 'api/routers/auth_jwt.py'), 'utf8');
  const routerPrefix = /APIRouter\(prefix="([^"]+)"/.exec(router)?.[1];
  const routes = [...router.matchAll(/@router\.get\(\s*"([^"]+)"/g)].map((match) => match[1]);
  const callback = routes.find((route) => route.includes('oauth') && route.includes('callback'));
  if (!apiBase || !routerPrefix || !callback) {
    throw new Error("The application's OAuth callback route could not be read");
  }
  return `${apiBase}${routerPrefix}${callback}`;
}

/** The route the callback leaves the visitor on, read from the app's route tree. */
function frontendCallbackRoute(): string {
  const appDir = join(WEB_DIR, 'src/app');
  const directory = join(appDir, '[locale]', 'auth', 'oauth', 'callback');
  if (!existsSync(join(directory, 'page.tsx'))) {
    throw new Error(`The application's callback page is not at ${directory}`);
  }
  const segments = directory
    .slice(appDir.length + 1)
    .split(sep)
    .filter((segment) => segment && !segment.startsWith('['));
  return `/${segments.join('/')}`;
}

/** Everything the flow needs, read from the application's own configuration. */
function applicationConfiguration() {
  const file = configurationFile();
  const settings = declaredSettings(file);
  const clientId = settings.GOOGLE_CLIENT_ID;
  const redirectUri = settings.GOOGLE_REDIRECT_URI;
  if (!clientId || !redirectUri) {
    throw new Error(`${file} declares no GOOGLE_CLIENT_ID / GOOGLE_REDIRECT_URI`);
  }
  const provider = providerConfiguration();
  return {
    file,
    clientId,
    redirectUri,
    scope: provider.scopes.join(' '),
    providerUrl: provider.authUrl,
    providerHost: new URL(provider.authUrl).hostname,
    apiCallbackRoute: apiCallbackRoute(),
    frontendCallbackRoute: frontendCallbackRoute(),
  };
}

/**
 * The authorization URL, built the way the application's provider builds it.
 *
 * The parameters are the provider's own (read from its module) and the
 * values are the application's configuration.
 */
function authorizationUrl(
  config: ReturnType<typeof applicationConfiguration>,
  state: string,
  redirectUri: string
): string {
  const url = new URL(config.providerUrl);
  url.searchParams.set('client_id', config.clientId);
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('scope', config.scope);
  url.searchParams.set('state', state);
  url.searchParams.set('access_type', 'offline');
  url.searchParams.set('prompt', 'consent');
  return url.toString();
}

/** The account the visitor is, once the provider has answered. */
const SIGNED_IN_USER = {
  id: 'oauth-user-001',
  email: 'oauth.user@example.com',
  full_name: 'OAuth User',
  role: 'user',
  is_active: true,
  is_verified: true,
  created_at: '2026-01-01T00:00:00Z',
};

/** The session the callback route leaves behind. */
const SESSION_TOKEN = 'oauth-session-token';

/** A route of the application that belongs to an account. */
const ACCOUNT_PATH = '/en/favorites';

type Flow = {
  /** The URL the browser was sent to. */
  providerUrl: URL | null;
  /** The request the callback route received, when it received one. */
  callbackRequest: { path: string; code: string | null; state: string | null } | null;
  /** Whether the visitor ended up with a session. */
  signedIn: boolean;
};

/**
 * Drive the sign-in.
 *
 * `redirectUri` overrides the one the configuration declares - that is how
 * the case with a redirect URI the application does not own is driven.
 */
async function signInWithGoogle(page: Page, options: { redirectUri?: string } = {}): Promise<Flow> {
  const config = applicationConfiguration();
  // The report names the configuration the run read, so a failure can be
  // read against the file it came from.
  test.info().annotations.push({ type: 'configuration', description: config.file });
  const publishedRedirectUri = options.redirectUri ?? config.redirectUri;
  const state = `state-${Math.random().toString(36).slice(2)}`;

  // The deployment says Google is configured, so the button is rendered.
  await page.route('**/api/v1/capabilities', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        auth: {
          jwt_enabled: true,
          demo_user_bypass: false,
          oauth: { google: true, apple: false },
        },
        email: { enabled: false, provider: 'dummy' },
        llm: { demo_mode: true, mode: 'local-model', provider: 'minimax', model: 'MiniMax-M3.1-Flash' },
        lead_capture: { waitlist_enabled: false },
        observability: { error_tracking: false },
      }),
    });
  });

  // The start endpoint: the application's answer, with the URL the provider
  // is to be sent to and the state the flow is identified by.
  await page.route('**/api/v1/auth/oauth/google', async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Set-Cookie': `oauth_state=${state}; Path=/; HttpOnly; SameSite=Lax`,
      },
      body: JSON.stringify({
        authorization_url: authorizationUrl(config, state, publishedRedirectUri),
      }),
    });
  });

  // The callback route: the session the application sets once the provider's
  // answer has been verified. The state has to come back unchanged, exactly
  // as the backend requires it.
  let callbackRequest: Flow['callbackRequest'] = null;
  let callbackAnswered: () => void = () => undefined;
  const callbackSeen = new Promise<void>((resolve) => {
    callbackAnswered = resolve;
  });
  await page.route(
    (url) => url.pathname === config.apiCallbackRoute,
    async (route) => {
      const url = new URL(route.request().url());
      callbackRequest = {
        path: url.pathname,
        code: url.searchParams.get('code'),
        state: url.searchParams.get('state'),
      };
      if (callbackRequest.state !== state) {
        await route.fulfill({
          status: 400,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ detail: 'Invalid OAuth state' }),
        });
        callbackAnswered();
        return;
      }
      await route.fulfill({
        status: 302,
        headers: {
          Location: new URL(config.frontendCallbackRoute, route.request().url()).toString(),
          'Set-Cookie': `access_token=${SESSION_TOKEN}; Path=/; HttpOnly; SameSite=Lax`,
        },
        body: '',
      });
      callbackAnswered();
    }
  );

  // The account behind the session. The application asks who the visitor is
  // with the cookie it holds, so the answer follows the cookie: without it
  // the visitor is anonymous, with it the visitor is the account.
  await page.route('**/api/v1/auth/me', async (route) => {
    const cookie = route.request().headers()['cookie'] ?? '';
    if (!cookie.includes(`access_token=${SESSION_TOKEN}`)) {
      await route.fulfill({
        status: 401,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'Not authenticated' }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(SIGNED_IN_USER),
    });
  });

  // The account's own route, so the session can be seen on it.
  await page.route('**/api/v1/favorites*', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: [], total: 0 }),
    });
  });
  await page.route('**/api/v1/collections*', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: [] }),
    });
  });

  // The provider, at the network boundary. Its answer sends the visitor back
  // to the route the application published - on the application's own origin,
  // so the flow stays on the application under test.
  let providerUrl: URL | null = null;
  let applicationOrigin = '';
  let providerAnswered: () => void = () => undefined;
  const providerSeen = new Promise<void>((resolve) => {
    providerAnswered = resolve;
  });
  await page.route(
    (url) => url.hostname === config.providerHost,
    async (route) => {
      providerUrl = new URL(route.request().url());
      const back = new URL(new URL(publishedRedirectUri).pathname, applicationOrigin);
      back.searchParams.set('code', 'stub-authorization-code');
      back.searchParams.set('state', providerUrl.searchParams.get('state') ?? '');
      // The provider's answer is a page that sends the visitor back. It is
      // a page and not a 302 on purpose: a redirect that follows an
      // intercepted response is not intercepted itself, and the callback
      // route has to be answered by this spec.
      const target = back.toString().replace(/&/g, '&amp;').replace(/"/g, '&quot;');
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
        body: `<!doctype html><html><head><meta http-equiv="refresh" content="0;url=${target}"></head><body>Signing you in…</body></html>`,
      });
      providerAnswered();
    }
  );

  await page.goto(LOGIN_PATH);
  applicationOrigin = new URL(page.url()).origin;

  const button = page.getByRole('button', { name: /google/i });
  await expect(button).toBeVisible({ timeout: 15000 });
  await button.click();

  // The click reaches the provider, and the provider's answer sends the
  // visitor back to the application. The flow ends either at the callback
  // route or wherever the provider was told to send the visitor.
  await providerSeen;
  await Promise.race([
    callbackSeen,
    page.waitForURL(
      (url) => url.hostname !== config.providerHost && url.pathname !== LOGIN_PATH,
      { timeout: 20000 }
    ),
  ]);

  // The callback route receives the visitor and leaves them on the
  // application's own page, which then forwards them.
  if (callbackRequest) {
    await page.waitForURL((url) => url.pathname.endsWith(config.frontendCallbackRoute), {
      timeout: 20000,
    });
    await page.waitForURL((url) => !url.pathname.includes('/auth/oauth/callback'), {
      timeout: 20000,
    });
  }

  const session = await page
    .context()
    .cookies(applicationOrigin)
    .then((cookies) => cookies.find((cookie) => cookie.name === 'access_token') ?? null);

  return { providerUrl, callbackRequest, signedIn: session !== null };
}

test.describe('The Google sign-in', () => {
  test('the click carries the application\'s own OAuth configuration and lands the visitor in a session', async ({
    page,
  }) => {
    const config = applicationConfiguration();

    const flow = await signInWithGoogle(page);

    // The browser went to the provider the application talks to.
    expect(flow.providerUrl, 'the click did not reach the provider').not.toBeNull();
    const providerUrl = flow.providerUrl as URL;
    expect(providerUrl.hostname).toBe(config.providerHost);

    // The redirect carries the configuration the application declares: the
    // client, the route the visitor comes back to, the scopes and the state.
    expect(providerUrl.searchParams.get('client_id')).toBe(config.clientId);
    expect(providerUrl.searchParams.get('redirect_uri')).toBe(config.redirectUri);
    expect(providerUrl.searchParams.get('scope')).toBe(config.scope);
    expect(providerUrl.searchParams.get('state')).toBeTruthy();

    // The provider sent the visitor back to the route the application owns,
    // with the state the flow started with.
    expect(flow.callbackRequest, 'the callback route was never reached').not.toBeNull();
    expect(flow.callbackRequest?.path).toBe(config.apiCallbackRoute);
    expect(flow.callbackRequest?.code).toBe('stub-authorization-code');
    expect(flow.callbackRequest?.state).toBe(providerUrl.searchParams.get('state'));

    // The session: the cookie is there, and the application knows who it
    // belongs to - the account's own route opens for the visitor instead of
    // the wall that asks for a sign-in.
    expect(flow.signedIn, 'the visitor ended up without a session').toBe(true);
    await page.goto(ACCOUNT_PATH);
    const main = page.getByRole('main');
    await expect(main.getByRole('heading', { name: /favorites/i }).first()).toBeVisible({
      timeout: 15000,
    });
    await expect(main.getByRole('link', { name: /sign in/i }).first()).toHaveCount(0);
    await expect(page.getByRole('button', { name: /user menu/i })).toBeVisible({
      timeout: 15000,
    });
  });

  test('a redirect URI the application does not own does not sign the visitor in', async ({
    page,
  }) => {
    const config = applicationConfiguration();

    // The same flow, with a redirect URI that is not the application's own
    // callback route.
    const flow = await signInWithGoogle(page, {
      redirectUri: new URL(`${config.apiCallbackRoute}/not-the-callback`, 'http://localhost').toString(),
    });

    // The provider sent the visitor somewhere the application does not
    // serve, so the callback never ran and no session was established.
    expect(flow.callbackRequest, 'the callback route answered a route it does not own').toBeNull();
    expect(flow.signedIn, 'a visitor without the application\'s callback route was signed in').toBe(
      false
    );

    await page.goto(ACCOUNT_PATH);
    const main = page.getByRole('main');
    await expect(main.getByRole('link', { name: /sign in/i }).first()).toBeVisible({
      timeout: 15000,
    });
  });
});
