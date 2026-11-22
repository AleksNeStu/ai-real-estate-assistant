# propvector

`propvector` is an open MIT command-line client for the
[AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
API — it is a client for an instance you point it at, not a hosted service,
and it talks to nothing but that instance.

The same command answers against a local self-hosted instance and against the
hosted one: the address comes from the environment.

## Install

```bash
npm install --global propvector-cli
```

Or run it from a checkout of this repository:

```bash
cd packages/cli
npm install
npm run build
node dist/index.js --help
```

## Use

```bash
export PROPVECTOR_API_URL=http://localhost:8000/api/v1
export PROPVECTOR_API_KEY=your-key

propvector valuation --city Kraków --street "Myśliwska" --area 60 --rooms 3
propvector search "two-room apartments in Krakow" --limit 5 --sort price
propvector chat "what does a flat in Krakow cost"
```

`--json` prints the answer exactly as the API returned it.

## The two variables

| Variable | Meaning |
|---|---|
| `PROPVECTOR_API_URL` | the API root, including the version prefix (`http://localhost:8000/api/v1`) |
| `PROPVECTOR_API_KEY` | the API key |

The key is read from the environment and from nowhere else. It is never
accepted as an argument — a command line is visible in the process list, in
the shell history and in every log that records it — and it is never asked
for at a prompt. The client refuses `--api-key` with an explanation.

## The contract

The client is typed against the published OpenAPI document,
`docs/api/openapi.json`, and the types in `src/generated/openapi.ts` are
generated from it. The test suite regenerates them and fails when they drift,
so the client cannot call an endpoint the contract does not describe.

## Licence

MIT — the same licence as the engine it talks to.
