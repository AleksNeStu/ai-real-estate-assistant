/**
 * Where the client points, and how it proves itself.
 *
 * Both come from the environment, and only from the environment: the base
 * URL decides which instance answers - a local self-hosted one or the hosted
 * one - and the key is a secret that must not travel through a command line
 * (a command line is visible in the process list, in the shell history and in
 * every log that records it) and must not be asked for interactively (a
 * prompt is a key on the screen, and a key typed at a prompt ends up in a
 * terminal buffer).
 *
 * So: `PROPVECTOR_API_URL` and `PROPVECTOR_API_KEY`, read once, never
 * written anywhere.
 */

/** The name of the variable the base URL comes from. */
export const URL_ENV = 'PROPVECTOR_API_URL';

/** The name of the variable the key comes from. */
export const KEY_ENV = 'PROPVECTOR_API_KEY';

/** The address the client reads when the environment names none. */
export const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1';

export interface ApiConfig {
  /** The root of the API, including the version prefix. */
  readonly baseUrl: string;
  /** The key the client sends. */
  readonly apiKey: string;
}

/** The environment did not say what the client needs to know. */
export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

/**
 * The configuration, read from the environment.
 *
 * The key is required: every operation the client calls is behind the API
 * key, and a request without it is a request that answers 401 - better to
 * say so before the request than after it.
 */
export function readConfig(env: NodeJS.ProcessEnv = process.env): ApiConfig {
  const rawUrl = env[URL_ENV]?.trim();
  const baseUrl = (rawUrl || DEFAULT_BASE_URL).replace(/\/+$/, '');

  let parsed: URL;
  try {
    parsed = new URL(baseUrl);
  } catch {
    throw new ConfigError(`${URL_ENV} is not a URL: ${rawUrl ?? ''}`);
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new ConfigError(`${URL_ENV} must be an http or https URL: ${rawUrl ?? ''}`);
  }

  const apiKey = env[KEY_ENV]?.trim();
  if (!apiKey) {
    throw new ConfigError(
      `${KEY_ENV} is not set. The key is read from the environment - it is never asked for at the prompt and never passed as an argument.`,
    );
  }

  return { baseUrl, apiKey };
}
