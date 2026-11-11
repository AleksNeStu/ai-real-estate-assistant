import { parseStructuredToolCalls, parseToolCall, parseToolCalls } from '../tool-calls';

describe('parseToolCall', () => {
  it('reads the name, the arguments and the answer out of an agent step', () => {
    const step =
      "(AgentAction(tool='search_properties', tool_input='query=\"Kraków\", rooms=2', log=''), '38 matches')";

    expect(parseToolCall(step)).toEqual({
      name: 'search_properties',
      args: 'query="Kraków", rooms=2',
      result: '38 matches',
    });
  });

  it('reads a step that is already a dictionary', () => {
    const step = { tool: 'neighborhood_quality', args: 'lat=50.07', observation: '7.5 / 10' };

    expect(parseToolCall(step)).toEqual({
      name: 'neighborhood_quality',
      args: 'lat=50.07',
      result: '7.5 / 10',
    });
  });

  it('drops a step that carries no tool', () => {
    expect(parseToolCall('the agent thought about it')).toBeNull();
    expect(parseToolCall({ note: 'nothing to see' })).toBeNull();
    expect(parseToolCall(null)).toBeNull();
  });
});

describe('parseToolCalls', () => {
  it('keeps the order the agent made the calls in', () => {
    const steps = [
      "(AgentAction(tool='search_properties', tool_input='query=\"Kraków\"', log=''), '38 matches')",
      "(AgentAction(tool='mortgage_calculator', tool_input='price=489000', log=''), '2 473 zł')",
    ];

    expect(parseToolCalls(steps).map((call) => call.name)).toEqual([
      'search_properties',
      'mortgage_calculator',
    ]);
  });

  it('reads nothing out of a trace that is not a list', () => {
    expect(parseToolCalls(undefined)).toEqual([]);
    expect(parseToolCalls('not a list')).toEqual([]);
  });
});

describe('parseStructuredToolCalls', () => {
  it('reads the calls the backend sends as data', () => {
    const calls = parseStructuredToolCalls([
      {
        name: 'search_properties',
        args: '{"query": "Kraków", "rooms": 2}',
        result: '38 matches',
      },
    ]);

    expect(calls).toEqual([
      {
        name: 'search_properties',
        args: '{"query": "Kraków", "rooms": 2}',
        result: '38 matches',
      },
    ]);
  });

  it('drops an entry that carries no tool name', () => {
    expect(
      parseStructuredToolCalls([{ args: '{}' }, { name: '   ' }, { name: 'mortgage_calculator' }])
    ).toEqual([{ name: 'mortgage_calculator', args: undefined, result: undefined }]);
  });

  it('reads nothing when the backend sent no calls', () => {
    expect(parseStructuredToolCalls(undefined)).toEqual([]);
    expect(parseStructuredToolCalls([])).toEqual([]);
    expect(parseStructuredToolCalls('tool_calls')).toEqual([]);
  });
});
