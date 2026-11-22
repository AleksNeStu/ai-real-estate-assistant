/**
 * The command line.
 *
 * One parser, three commands, one place that decides what a wrong argument
 * looks like. The key is never one of the arguments: it comes from the
 * environment, and an attempt to pass it as an argument is refused with an
 * explanation rather than quietly ignored.
 */

import { ApiClient, ApiError, NetworkError } from './client.js';
import { ConfigError, readConfig } from './config.js';
import { OPERATIONS } from './contract.js';
import { runChat, formatChat } from './commands/chat.js';
import { runSearch, formatSearch } from './commands/search.js';
import { runValuation, formatValuation } from './commands/valuation.js';
import type { SortField, SortOrder } from './generated/openapi.js';

export interface Io {
  out(text: string): void;
  err(text: string): void;
}

const defaultIo: Io = {
  out: (text) => process.stdout.write(`${text}\n`),
  err: (text) => process.stderr.write(`${text}\n`),
};

/** The command was asked for something that cannot work. */
export class UsageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UsageError';
  }
}

interface ParsedArgs {
  positionals: string[];
  flags: Map<string, string | true>;
}

/** `--name value`, `--name=value` and `--name` are all accepted. */
export function parseArgs(argv: string[]): ParsedArgs {
  const positionals: string[] = [];
  const flags = new Map<string, string | true>();

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? '';
    if (!arg.startsWith('--')) {
      positionals.push(arg);
      continue;
    }
    const body = arg.slice(2);
    const equals = body.indexOf('=');
    if (equals >= 0) {
      flags.set(body.slice(0, equals), body.slice(equals + 1));
      continue;
    }
    const next = argv[index + 1];
    if (next !== undefined && !next.startsWith('--')) {
      flags.set(body, next);
      index += 1;
    } else {
      flags.set(body, true);
    }
  }

  return { positionals, flags };
}

function stringFlag(flags: Map<string, string | true>, name: string): string | undefined {
  const value = flags.get(name);
  if (value === undefined) return undefined;
  if (value === true) {
    throw new UsageError(`--${name} needs a value.`);
  }
  return value;
}

function numberFlag(flags: Map<string, string | true>, name: string): number | undefined {
  const raw = stringFlag(flags, name);
  if (raw === undefined) return undefined;
  const value = Number(raw);
  if (!Number.isFinite(value)) {
    throw new UsageError(`--${name} needs a number, not "${raw}".`);
  }
  return value;
}

const SORT_FIELDS: SortField[] = [
  'relevance',
  'price',
  'price_per_sqm',
  'area_sqm',
  'year_built',
];
const SORT_ORDERS: SortOrder[] = ['asc', 'desc'];

/** The options each command accepts, for the refusal of an unknown one. */
const ACCEPTED: Record<string, string[]> = {
  valuation: ['--city', '--street', '--area', '--rooms', '--property-id', '--json'],
  search: ['--query', '--limit', '--sort', '--order', '--json'],
  chat: ['--message', '--session-id', '--json'],
};

function refuseUnknownFlags(command: string, flags: Map<string, string | true>): void {
  const accepted = ACCEPTED[command] ?? [];
  for (const name of flags.keys()) {
    if (name === 'help') continue;
    if (!accepted.includes(`--${name}`)) {
      throw new UsageError(
        `Unknown option --${name} for "${command}". Accepted: ${accepted.join(', ')}.`,
      );
    }
  }
}

/** The key must not travel through the command line. */
function refuseKeyArguments(flags: Map<string, string | true>): void {
  for (const name of ['api-key', 'api_key', 'key', 'token', 'apikey']) {
    if (flags.has(name)) {
      throw new UsageError(
        `The key is read from PROPVECTOR_API_KEY, never from an argument - a command line is visible in the process list and in the shell history.`,
      );
    }
  }
}

export const USAGE = `propvector - an open command-line client for the AI Real Estate Assistant API.

Usage:
  propvector valuation --city Krakow --street "Mysliwska" [--area 60] [--rooms 3] [--property-id ID]
  propvector search "two-room apartments in Krakow" [--limit 5] [--sort price] [--order asc]
  propvector chat "what does a flat in Krakow cost" [--session-id ID]

Options:
  --json    print the answer as the API returned it
  --help    this text

Environment:
  PROPVECTOR_API_URL   the API root, including the version prefix
                       (for example http://localhost:8000/api/v1)
  PROPVECTOR_API_KEY   the API key - read from the environment, never from
                       an argument and never from a prompt`;

async function runCommand(
  command: string,
  parsed: ParsedArgs,
  client: ApiClient,
): Promise<{ text: string; json: unknown }> {
  if (command === 'valuation') {
    const options = {
      city: stringFlag(parsed.flags, 'city'),
      street: stringFlag(parsed.flags, 'street'),
      areaSqm: numberFlag(parsed.flags, 'area'),
      rooms: numberFlag(parsed.flags, 'rooms'),
      propertyId: stringFlag(parsed.flags, 'property-id'),
    };
    if (!options.propertyId && !(options.city && options.street)) {
      throw new UsageError(
        'valuation needs --city and --street, or --property-id.',
      );
    }
    const answer = await runValuation(client, options);
    return { text: formatValuation(answer), json: answer };
  }

  if (command === 'search') {
    const query = stringFlag(parsed.flags, 'query') ?? parsed.positionals.join(' ');
    if (!query.trim()) {
      throw new UsageError('search needs a query, as an argument or as --query.');
    }
    const sortBy = stringFlag(parsed.flags, 'sort');
    if (sortBy && !SORT_FIELDS.includes(sortBy as SortField)) {
      throw new UsageError(
        `--sort accepts ${SORT_FIELDS.join(', ')}, not "${sortBy}".`,
      );
    }
    const sortOrder = stringFlag(parsed.flags, 'order');
    if (sortOrder && !SORT_ORDERS.includes(sortOrder as SortOrder)) {
      throw new UsageError(`--order accepts ${SORT_ORDERS.join(', ')}, not "${sortOrder}".`);
    }
    const answer = await runSearch(client, {
      query,
      limit: numberFlag(parsed.flags, 'limit'),
      sortBy: sortBy as SortField | undefined,
      sortOrder: sortOrder as SortOrder | undefined,
    });
    return { text: formatSearch(answer), json: answer };
  }

  if (command === 'chat') {
    const message = stringFlag(parsed.flags, 'message') ?? parsed.positionals.join(' ');
    if (!message.trim()) {
      throw new UsageError('chat needs a message, as an argument or as --message.');
    }
    const answer = await runChat(client, {
      message,
      sessionId: stringFlag(parsed.flags, 'session-id'),
    });
    return { text: formatChat(answer), json: answer };
  }

  throw new UsageError(`Unknown command "${command}".`);
}

export async function main(
  argv: string[],
  env: NodeJS.ProcessEnv = process.env,
  io: Io = defaultIo,
): Promise<number> {
  const [command, ...rest] = argv;

  if (!command || command === '--help' || command === 'help') {
    io.out(USAGE);
    return command ? 0 : 2;
  }

  const parsed = parseArgs(rest);
  if (parsed.flags.get('help') === true) {
    io.out(USAGE);
    return 0;
  }

  try {
    refuseKeyArguments(parsed.flags);
    refuseUnknownFlags(command, parsed.flags);

    const config = readConfig(env);
    const client = new ApiClient(config);
    const { text, json } = await runCommand(command, parsed, client);

    if (parsed.flags.get('json') === true) {
      io.out(JSON.stringify(json, null, 2));
    } else {
      io.out(text);
    }
    return 0;
  } catch (error) {
    if (error instanceof UsageError || error instanceof ConfigError) {
      io.err(String(error.message));
      return 2;
    }
    if (error instanceof ApiError || error instanceof NetworkError) {
      io.err(String(error.message));
      return 1;
    }
    io.err(error instanceof Error ? error.message : String(error));
    return 1;
  }
}

/** The operations the client calls, named for the help text and the tests. */
export const CALLED_OPERATIONS = OPERATIONS;
