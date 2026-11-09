/**
 * The tool calls of an answer.
 *
 * The chat stream carries the agent's intermediate steps, sanitized for the
 * client. They arrive in two shapes: the agent's own steps, which are a
 * stringified `(AgentAction, observation)` pair, and the web research
 * agent's steps, which are dictionaries. Both are read here, once, so the
 * chat can draw a card per call and never has to know how the agent spells
 * a step.
 */

export interface ToolCall {
  /** The tool's name, in mono: `search_properties`. */
  name: string;
  /** The arguments the tool was called with. */
  args?: string;
  /** What the tool answered. */
  result?: string;
}

const NAME_PATTERN = /tool='([^']*)'/;
const ARGS_PATTERN = /tool_input='([\s\S]*?)',\s*log=/;
const OBSERVATION_PATTERN = /\),\s*'([\s\S]*)'\)\s*$/;

const NAME_KEYS = ['tool', 'name', 'tool_name', 'action'];
const ARGS_KEYS = ['tool_input', 'args', 'arguments', 'input', 'parameters'];
const RESULT_KEYS = ['observation', 'result', 'output', 'content', 'return', 'value'];

/** The repr of a Python string escapes these; the text itself does not. */
function unescape(value: string): string {
  return value
    .replace(/\\'/g, "'")
    .replace(/\\"/g, '"')
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '\t')
    .replace(/\\\\/g, '\\');
}

function firstString(record: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.length > 0) return value;
  }
  return undefined;
}

/**
 * One step of the agent's trace, read as a tool call.
 *
 * A step that carries no tool name is not a call - it is a note - and is
 * dropped rather than guessed at.
 */
export function parseToolCall(step: unknown): ToolCall | null {
  if (typeof step === 'string') {
    const name = NAME_PATTERN.exec(step)?.[1];
    if (!name) return null;

    const args = ARGS_PATTERN.exec(step)?.[1];
    const observation = OBSERVATION_PATTERN.exec(step)?.[1];

    return {
      name,
      args: args ? unescape(args) : undefined,
      result: observation ? unescape(observation) : undefined,
    };
  }

  if (step && typeof step === 'object') {
    const record = step as Record<string, unknown>;
    const name = firstString(record, NAME_KEYS);
    if (!name) return null;

    return {
      name,
      args: firstString(record, ARGS_KEYS),
      result: firstString(record, RESULT_KEYS),
    };
  }

  return null;
}

/** Every tool call of a trace, in the order the agent made them. */
export function parseToolCalls(steps: unknown): ToolCall[] {
  if (!Array.isArray(steps)) return [];
  return steps
    .map((step) => parseToolCall(step))
    .filter((call): call is ToolCall => call !== null);
}
