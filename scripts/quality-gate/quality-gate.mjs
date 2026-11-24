#!/usr/bin/env node
// quality-gate.mjs - the AI-code quality gate (Rule 383).
//
// VENDORED FILE. The source of truth is nest-solo/templates/quality-gate/quality-gate.mjs;
// a product carries a copy at scripts/quality-gate/quality-gate.mjs because a product repo
// runs standalone in CI. Do not edit the copy - edit the template and re-vendor
// (pwsh nest-solo/scripts/quality/vendor-quality-gate.ps1).
//
// Generic checks live here; everything product-specific lives in <product>/quality-gate.json.
// Node >= 20, no dependencies. Exit 0 = green, 1 = a blocking check failed, 2 = config error.
//
// Usage (agent / CI; the operator never types this - run-local-ci.ps1 and the workflow do):
//   node scripts/quality-gate/quality-gate.mjs --mode quick|preclose|full
//        [--base <git-ref>] [--only a,b] [--skip a,b] [--update-baseline] [--json]

import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { builtinModules } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const GATE_VERSION = '1.0.0';

// ─── args ────────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const arg = (name, def = null) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : def;
};
const flag = (name) => argv.includes(`--${name}`);
const MODE = arg('mode', 'preclose');
if (!['quick', 'preclose', 'full'].includes(MODE)) die(2, `unknown --mode '${MODE}' (quick|preclose|full)`);
const ONLY = (arg('only') || '').split(',').filter(Boolean);
const SKIP_ARG = (arg('skip') || '').split(',').filter(Boolean);
const UPDATE_BASELINE = flag('update-baseline');
const JSON_OUT = flag('json');
const IN_CI = !!process.env.CI;

// ─── root + config ───────────────────────────────────────────────────────────
const ROOT = findRoot(process.cwd());
const CFG_PATH = path.join(ROOT, 'quality-gate.json');
const DEFAULTS = {
  sourceDirs: ['src', 'app', 'lib', 'pages', 'components', 'server', 'scripts'],
  ignoreDirs: ['node_modules', '.next', 'dist', 'build', 'coverage', 'out', '.turbo', '.vercel',
    'playwright-report', 'test-results', '.venv', '.venv-uv', 'venv', '__pycache__', '.pytest_cache',
    '.mypy_cache', '.ruff_cache', '.quality-gate'],
  diffSlop: { patterns: 'default', allowMarker: 'quality-gate-allow:' },
  deps: { minAgeDays: 7, minWeeklyDownloads: 100, exactPins: true, allowUnlisted: [] },
  sast: {
    rulesets: ['p/owasp-top-ten', 'p/security-audit'], extraRulesets: [], image: 'semgrep/semgrep:1.94.0',
    runner: 'auto', baseline: '.quality-gate/semgrep-baseline.json', blockSeverity: ['ERROR'], targets: [],
  },
  supplyChain: { blockSeverity: ['critical', 'high'], requireFixAvailable: true, ignore: [] },
  determinism: { script: 'test:shuffle' },
  slop: {
    baseline: '.quality-gate/slop-baseline.json', duplicationTolerancePct: 0.5,
    jscpd: '5.4.3', knip: '6.44.2', knipIssueTolerance: 0,
  },
  perf: { jsBudgetKb: null, chunksDir: '.next/static/chunks', lighthouse: null },
  evals: null,
  extraChecks: [],
  skip: [],
};
const CONFIG = loadConfig();

// ─── git / diff ──────────────────────────────────────────────────────────────
const BASE = resolveBase();
const DIFF = loadDiff();

// ─── checks registry ─────────────────────────────────────────────────────────
const CHECKS = [
  { id: 'diff-slop', modes: ['quick', 'preclose', 'full'], run: checkDiffSlop },
  { id: 'dep-reality', modes: ['quick', 'preclose', 'full'], run: checkDepReality },
  { id: 'lockfile', modes: ['full'], run: checkLockfile },
  { id: 'sast', modes: ['preclose', 'full'], run: checkSast },
  { id: 'supply-chain', modes: ['full'], run: checkSupplyChain },
  { id: 'determinism', modes: ['preclose', 'full'], run: checkDeterminism },
  { id: 'slop-signals', modes: ['full'], run: checkSlopSignals },
  { id: 'perf-budget', modes: ['full'], run: checkPerfBudget },
  { id: 'evals', modes: ['full'], run: checkEvals },
  ...CONFIG.extraChecks.map((c) => ({
    id: `extra:${c.name}`, modes: c.modes || ['full'], run: () => runCommandCheck(c.command, c.env),
  })),
];

// ─── main ────────────────────────────────────────────────────────────────────
const results = [];
const started = Date.now();
for (const check of CHECKS) {
  if (!check.modes.includes(MODE)) continue;
  if (ONLY.length && !ONLY.includes(check.id)) continue;
  const cfgSkip = CONFIG.skip.find((s) => s.check === check.id);
  if (cfgSkip) { results.push(res(check.id, 'skip', `quality-gate.json: ${cfgSkip.reason}`)); continue; }
  if (SKIP_ARG.includes(check.id)) { results.push(res(check.id, 'skip', 'skipped by the caller (--skip)')); continue; }
  const t0 = Date.now();
  let r;
  try { r = await check.run(); } catch (e) { r = { status: 'fail', summary: `check crashed: ${e.message}` }; }
  r.id = check.id; r.ms = Date.now() - t0;
  results.push(r);
}
report();

// ═════════════════════════════════════════════════════════════════════════════
// Checks
// ═════════════════════════════════════════════════════════════════════════════

// diff-slop: suppression and focus markers an agent adds to make red things go green.
function checkDiffSlop() {
  const JS = /\.(?:[cm]?[jt]sx?)$/; const PY = /\.py$/; const TEST = /(?:\.|\/)(?:test|spec)s?\.|__tests__\/|(?:^|\/)tests?\//;
  const defaults = [
    { id: 'eslint-disable', re: /eslint-disable(?:-next-line|-line)?\b/, files: JS },
    { id: 'ts-suppress', re: /@ts-(?:ignore|nocheck|expect-error)\b/, files: JS },
    { id: 'as-any', re: /\bas\s+any\b|<any>/, files: JS },
    { id: 'focused-or-skipped-test', re: /\b(?:it|test|describe)\.(?:only|skip)\s*\(|\b(?:fit|fdescribe|xit|xdescribe)\s*\(/, files: JS, testsOnly: true },
    { id: 'py-suppress', re: /#\s*type:\s*ignore|#\s*noqa\b|#\s*pragma:\s*no\s*cover/, files: PY },
    { id: 'py-skip', re: /@pytest\.mark\.(?:skip|xfail)\b/, files: PY, testsOnly: true },
  ];
  const patterns = defaults.filter((p) => !(CONFIG.diffSlop.disable || []).includes(p.id));
  const marker = CONFIG.diffSlop.allowMarker;
  const hits = [];
  for (const f of DIFF.files) {
    if (isGateFile(f.path)) continue;
    for (const line of f.added) {
      for (const p of patterns) {
        if (!p.files.test(f.path) || (p.testsOnly && !TEST.test(f.path))) continue;
        if (!p.re.test(line.text)) continue;
        const allow = line.text.split(marker)[1];
        if (allow !== undefined && allow.trim().length > 3) continue; // a written reason is an explicit decision
        hits.push(`${f.path}:${line.n} [${p.id}] ${line.text.trim().slice(0, 120)}`);
      }
    }
  }
  if (!DIFF.files.length) return { status: 'pass', summary: `no changes vs ${BASE.label}` };
  return hits.length
    ? { status: 'fail', summary: `${hits.length} new suppression/focus marker(s) - fix the cause, or add '${marker} <reason>' on the line`, details: hits }
    : { status: 'pass', summary: `${DIFF.files.length} changed file(s), no new suppressions` };
}

// dep-reality: hallucinated / slopsquatted / unpinned dependencies and undeclared imports.
async function checkDepReality() {
  const problems = []; const warnings = [];
  // (a) new or changed declared dependencies (node + python)
  for (const pj of findManifests('package.json')) {
    const rel = path.relative(ROOT, pj).replaceAll('\\', '/');
    const now = BASE.kind === 'staged' ? readJsonAt('', rel) : readJson(pj); const before = readJsonAt(BASE.ref, rel);
    for (const [name, spec, section] of changedDeps(before, now)) {
      if (CONFIG.deps.exactPins && section !== 'peerDependencies' && !isExactNpmSpec(spec)) {
        problems.push(`${rel}: ${name}@${spec} - not an exact pin (Rule 383: new deps are exact)`);
      }
      if (/^(?:workspace|file|link|catalog|portal|git\+?|https?):/.test(spec)) continue;
      const realName = spec.startsWith('npm:') ? spec.slice(4).replace(/@[^@]*$/, '') : name;
      const pinned = (spec.startsWith('npm:') ? spec.replace(/^npm:.+@/, '') : spec);
      const v = await verifyNpm(realName, isExactNpmSpec(pinned) ? pinned : null);
      (v.level === 'fail' ? problems : warnings).push(...(v.msg ? [`${rel}: ${realName} - ${v.msg}`] : []));
    }
  }
  for (const req of findManifests(/^requirements[\w.-]*\.txt$/)) {
    const rel = path.relative(ROOT, req).replaceAll('\\', '/');
    const added = (DIFF.files.find((f) => f.path === rel)?.added || []).map((l) => l.text.trim())
      .filter((t) => t && !t.startsWith('#') && !t.startsWith('-'));
    for (const lineText of added) {
      const m = lineText.match(/^([A-Za-z0-9_.\-\[\]]+)\s*(.*)$/);
      if (!m) continue;
      const name = m[1].replace(/\[.*\]$/, '');
      if (CONFIG.deps.exactPins && !/^==\s*[\w.+!-]+/.test(m[2])) problems.push(`${rel}: ${lineText} - not an exact '==' pin`);
      const v = await verifyPypi(name);
      (v.level === 'fail' ? problems : warnings).push(...(v.msg ? [`${rel}: ${name} - ${v.msg}`] : []));
    }
  }
  // (b) imports that resolve to no declared dependency
  const declared = declaredNodeDeps();
  if (declared) {
    const aliases = tsPathAliases();
    const files = MODE === 'full' ? listSourceFiles() : DIFF.files.filter((f) => !f.deleted).map((f) => f.path);
    for (const rel of files.filter((f) => /\.(?:[cm]?[jt]sx?)$/.test(f) && !isGateFile(f))) {
      let src; try { src = fs.readFileSync(path.join(ROOT, rel), 'utf8'); } catch { continue; }
      for (const spec of importSpecifiers(src)) {
        if (/^[./]|^node:|^#|^virtual:|^data:|^https?:/.test(spec)) continue;
        if (aliases.some((a) => spec === a || spec.startsWith(a.endsWith('/') ? a : `${a}/`))) continue;
        const pkg = spec.startsWith('@') ? spec.split('/').slice(0, 2).join('/') : spec.split('/')[0];
        if (builtinModules.includes(pkg) || declared.has(pkg) || declared.has(`@types/${pkg.replace(/^@/, '').replace('/', '__')}`)) continue;
        if (CONFIG.deps.allowUnlisted.includes(pkg)) continue;
        problems.push(`${rel}: imports '${pkg}', which no package.json declares (hallucinated or transitive-only)`);
      }
    }
  }
  const uniq = [...new Set(problems)];
  if (uniq.length) return { status: 'fail', summary: `${uniq.length} dependency problem(s)`, details: [...uniq, ...warnings.map((w) => `WARN ${w}`)] };
  return { status: warnings.length ? 'warn' : 'pass', summary: warnings.length ? `${warnings.length} registry check(s) unverified` : 'declared deps real and pinned; imports declared', details: warnings };
}

function checkLockfile() {
  if (exists('pnpm-lock.yaml')) {
    const r = sh('pnpm', ['install', '--frozen-lockfile', '--lockfile-only', '--ignore-scripts'], { timeout: 240_000 });
    return r.code === 0 ? { status: 'pass', summary: 'pnpm-lock.yaml matches package.json' }
      : { status: 'fail', summary: 'pnpm-lock.yaml is out of date with package.json (frozen install refused)', details: tail(r.out) };
  }
  if (exists('uv.lock')) {
    const r = sh('uv', ['lock', '--check']);
    return r.code === 0 ? { status: 'pass', summary: 'uv.lock is current' } : { status: 'fail', summary: 'uv.lock is stale', details: tail(r.out) };
  }
  if (exists('package-lock.json')) {
    // Prove it frozen: regenerate the lockfile in a scratch copy and compare. A --dry-run install
    // succeeds against a stale lockfile, so it proves nothing.
    // npm workspaces: the scratch copy would miss every workspace manifest, so the comparison would
    // be wrong both ways - say NOT CHECKED rather than guess (cross-model review, 2026-11-23).
    if (readJsonSafe(path.join(ROOT, 'package.json'))?.workspaces) {
      return { status: IN_CI ? 'fail' : 'warn', summary: 'NOT CHECKED: npm workspaces - the scratch-copy freeze check does not model them; skip lockfile with a reason in quality-gate.json, or check it in CI with npm ci' };
    }
    const tmp = fs.mkdtempSync(path.join(osTmp(), 'qg-lock-'));
    for (const f of ['package.json', 'package-lock.json', '.npmrc']) if (exists(f)) fs.copyFileSync(path.join(ROOT, f), path.join(tmp, f));
    const r = spawnSync('npm', ['install', '--package-lock-only', '--ignore-scripts', '--no-audit', '--no-fund'], { cwd: tmp, encoding: 'utf8', timeout: 240_000, shell: process.platform === 'win32' });
    if (r.status !== 0) return { status: 'fail', summary: 'package-lock.json does not resolve', details: tail(`${r.stdout}\n${r.stderr}`) };
    const norm = (p) => { const j = readJsonSafe(p) || {}; delete j.name; delete j.version; return JSON.stringify(j.packages || j.dependencies || {}); };
    return norm(path.join(ROOT, 'package-lock.json')) === norm(path.join(tmp, 'package-lock.json'))
      ? { status: 'pass', summary: 'package-lock.json matches package.json' }
      : { status: 'fail', summary: 'package-lock.json is out of date with package.json (a fresh resolve rewrites it) - run npm install and commit the lockfile' };
  }
  return { status: 'skip', summary: 'no lockfile found' };
}

// sast: OWASP Top 10 + security-audit + the gate's AI-code rules, baseline-relative.
function checkSast() {
  // WHAT the full scan covers is a product decision, not a constant.
  //
  // Scanning '.' is right for a small repository and wrong for one that
  // carries vendored trees: measured 2026-11-23 on ps, the whole-tree scan
  // spent its whole 900 s budget and produced NO JSON, because the tree
  // holds 26 000 files under apps/backend/.venv + .venv-uv. The scan now
  // covers, in order: the targets the product declares, the declared
  // sourceDirs, and only then the whole tree.
  const declaredTargets = (CONFIG.sast.targets || []).filter((d) => exists(d));
  const sourceTargets = CONFIG.sourceDirs.filter((d) => exists(d));
  const fullTargets = declaredTargets.length ? declaredTargets : (sourceTargets.length ? sourceTargets : ['.']);
  const targets = MODE === 'full' ? fullTargets : DIFF.files.filter((f) => !f.deleted && /\.(?:[cm]?[jt]sx?|py|go|java|rb|php|ya?ml|tf|dockerfile)$/i.test(f.path) && !isGateFile(f.path)).map((f) => f.path);
  if (!targets.length) return { status: 'pass', summary: 'no changed code files to scan' };
  const scanTargets = targets.length > 300 ? ['.'] : targets;
  const configs = [...CONFIG.sast.rulesets, ...CONFIG.sast.extraRulesets, gateRelPath('semgrep/ai-code.yml')];
  // `--no-git-ignore` is not a preference, it is the difference between a scan
  // and no scan at all for a product that is a git SUBMODULE.
  //
  // Measured 2026-11-23 (ps): semgrep runs in a container that mounts the
  // product at /src. A submodule's `.git` is a FILE that points at the
  // meta-repo's gitdir (`gitdir: ../../../.git/modules/products/large/ps`),
  // and that path does not exist inside the container - so semgrep's git call
  // fails ("fatal: not a git repository"), the run produced no JSON, and the
  // gate reported SAST NOT CHECKED. The git call exists only to honour
  // .gitignore, and the gate already excludes what it means to exclude
  // (node_modules, .venv, .next, ...), so the ignore lookup buys nothing and
  // costs the whole check.
  const semArgs = ['scan', '--json', '--metrics=off', '--disable-version-check', '--timeout', '30', '--quiet', '--no-git-ignore',
    ...configs.flatMap((c) => ['--config', c]),
    // The excludes must be GLOBS. A bare directory name (`--exclude node_modules`)
    // is matched against the WHOLE path, so it matches nothing and the scan
    // walked the vendored trees: measured 2026-11-23 on ps, 26 356 files under
    // apps/backend/.venv + .venv-uv, and a 20-minute scan that blew the
    // 900 s budget. `**/<dir>/**` is what actually excludes the tree.
    ...[...new Set([...CONFIG.ignoreDirs, '.git'])].flatMap((d) => ['--exclude', `**/${d}/**`]),
    ...scanTargets];
  const runner = pickSemgrepRunner();
  if (!runner) return { status: IN_CI || MODE === 'full' ? 'fail' : 'warn', summary: 'semgrep unavailable (no docker, no semgrep CLI) - SAST NOT CHECKED' };
  // The container is NAMED so a timeout can take it down. `docker run --rm`
  // removes the container when it EXITS - an orphan that never exits stays,
  // holds its image layer and competes for the CPU with the next run.
  const container = `qg-semgrep-${process.pid}-${Date.now().toString(36)}`;
  const killContainer = () => { try { spawnSync('docker', ['rm', '-f', container], { timeout: 60_000 }); } catch { /* best effort */ } };
  const r = runner === 'docker'
    ? sh('docker', ['run', '--rm', '--name', container, '-v', `${ROOT}:/src`, '-w', '/src', CONFIG.sast.image, 'semgrep', ...semArgs], { timeout: 900_000, onTimeout: killContainer })
    : sh('semgrep', semArgs, { timeout: 900_000 });
  let parsed; try { parsed = JSON.parse(r.stdout); } catch { return { status: 'fail', summary: `semgrep produced no JSON (exit ${r.code}) - SAST NOT CHECKED`, details: tail(r.out) }; }
  const findings = (parsed.results || []).map((x) => ({
    fp: sha(`${x.check_id}|${x.path}|${(x.extra?.lines || '').replace(/\s+/g, ' ').trim()}`),
    check: x.check_id, path: x.path, line: x.start?.line, sev: x.extra?.severity, msg: (x.extra?.message || '').split('\n')[0].slice(0, 160),
  }));
  const blPath = path.join(ROOT, CONFIG.sast.baseline);
  if (UPDATE_BASELINE && MODE === 'full') {
    writeJson(blPath, { gate: GATE_VERSION, generated: new Date().toISOString(), note: 'Accepted pre-existing findings. Shrink it; never grow it by hand.', findings: findings.map(({ fp, check, path: p }) => ({ fp, check, path: p })) });
    return { status: 'pass', summary: `baseline written: ${findings.length} finding(s) -> ${CONFIG.sast.baseline}` };
  }
  const known = new Set((readJsonSafe(blPath)?.findings || []).map((f) => f.fp));
  const fresh = findings.filter((f) => !known.has(f.fp));
  const blocking = fresh.filter((f) => CONFIG.sast.blockSeverity.includes(f.sev));
  const advisory = fresh.filter((f) => !CONFIG.sast.blockSeverity.includes(f.sev));
  const lines = (arr) => arr.map((f) => `${f.path}:${f.line} [${f.sev}] ${f.check} - ${f.msg}`);
  const scanned = parsed.paths?.scanned?.length ?? 0;
  // Targets in, nothing scanned out = NOT CHECKED, in every mode. Measured 2026-11-23: one
  // preclose run in a submodule printed "0 file(s) scanned" for 8 changed files and passed.
  if (scanned === 0) return { status: 'fail', summary: `semgrep scanned 0 of ${scanTargets.length === 1 && scanTargets[0] === '.' ? 'the tree' : `${scanTargets.length} target(s)`} - SAST NOT CHECKED (re-run; a not-checked scan is never a pass)`, details: [...(parsed.errors || []).slice(0, 5).map((e) => e.message), ...tail(r.out, 5)] };
  if (blocking.length) return { status: 'fail', summary: `${blocking.length} new ${CONFIG.sast.blockSeverity.join('/')} finding(s) (${scanned} files, ${runner})`, details: [...lines(blocking), ...lines(advisory).map((l) => `ADVISORY ${l}`)] };
  return { status: advisory.length ? 'warn' : 'pass', summary: `${scanned} file(s) scanned via ${runner}; ${advisory.length} new advisory, ${findings.length - fresh.length} baselined`, details: lines(advisory) };
}

function checkSupplyChain() {
  // An ignore entry expires on its `until` date - an accepted advisory is re-judged, never forgotten.
  const today = new Date().toISOString().slice(0, 10);
  const ignore = new Set(CONFIG.supplyChain.ignore.filter((i) => !i.until || i.until >= today).map((i) => i.id));
  if (exists('pnpm-lock.yaml') || exists('package-lock.json')) {
    const pm = exists('pnpm-lock.yaml') ? 'pnpm' : 'npm';
    // Production scope is computed HERE, from each finding's dependency path: pnpm 10.28's
    // `audit --prod` returned the same 38 advisories as a plain `audit` (measured 2026-11-23).
    const r = sh(pm, ['audit', '--json'], { timeout: 180_000 });
    let j; try { j = JSON.parse(r.stdout); } catch { return { status: 'fail', summary: `${pm} audit returned no JSON (registry unreachable?) - NOT CHECKED`, details: tail(r.out) }; }
    const pkg = readJsonSafe(path.join(ROOT, 'package.json')) || {};
    const prodRoots = new Set([...Object.keys(pkg.dependencies || {}), ...Object.keys(pkg.optionalDependencies || {})]);
    const rootOf = (p) => String(p).split('>').filter((s) => s && s !== '.')[0];
    const rows = [];
    if (j.advisories) {
      for (const a of Object.values(j.advisories)) {
        const paths = (a.findings || []).flatMap((f) => f.paths || []);
        rows.push({ id: a.github_advisory_id || String(a.id), sev: a.severity, pkg: a.module_name, fix: !!a.patched_versions && a.patched_versions !== '<0.0.0', title: a.title, prod: !paths.length || paths.some((p) => prodRoots.has(rootOf(p))) });
      }
    } else if (j.vulnerabilities) {
      for (const [name, v] of Object.entries(j.vulnerabilities)) rows.push({ id: name, sev: v.severity, pkg: name, fix: !!v.fixAvailable, title: (v.via || []).map((x) => x.title || x).join('; '), prod: !v.dev });
    }
    const blocking = rows.filter((x) => x.prod && CONFIG.supplyChain.blockSeverity.includes(x.sev) && (!CONFIG.supplyChain.requireFixAvailable || x.fix) && !ignore.has(x.id));
    const fmt = (x) => `${x.sev.toUpperCase()} ${x.pkg} ${x.id} ${x.prod ? 'prod' : 'dev'} ${x.fix ? '(fix available)' : '(no fix)'} - ${String(x.title).slice(0, 100)}`;
    const dedupe = (arr) => [...new Set(arr.map(fmt))];
    return blocking.length ? { status: 'fail', summary: `${blocking.length} fixable ${CONFIG.supplyChain.blockSeverity.join('/')} advisory(ies) in production deps`, details: dedupe(blocking) }
      : { status: rows.length ? 'warn' : 'pass', summary: `${rows.length} advisory(ies) (${rows.filter((x) => !x.prod).length} dev-only), none blocking`, details: dedupe(rows.filter((x) => CONFIG.supplyChain.blockSeverity.includes(x.sev))).slice(0, 20) };
  }
  if (exists('requirements.txt') || exists('pyproject.toml')) {
    const r = sh('pip-audit', ['--format', 'json', ...(exists('requirements.txt') ? ['-r', 'requirements.txt'] : [])], { timeout: 300_000 });
    if (r.code === null || /not recognized|not found|ENOENT/.test(r.out)) return { status: IN_CI ? 'fail' : 'warn', summary: 'pip-audit not installed - NOT CHECKED' };
    return r.code === 0 ? { status: 'pass', summary: 'pip-audit: no known vulnerabilities' } : { status: 'fail', summary: 'pip-audit reported vulnerabilities', details: tail(r.out) };
  }
  return { status: 'skip', summary: 'no lockfile / python manifest' };
}

// determinism: the suite again in a shuffled order - an order-dependent or time/random-dependent
// test fails here. The command is the product's own `test:shuffle` script (project-specific).
function checkDeterminism() {
  const pkg = readJsonSafe(path.join(ROOT, 'package.json'));
  const script = CONFIG.determinism.script;
  if (pkg && pkg.scripts?.[script]) {
    const r = sh(exists('pnpm-lock.yaml') ? 'pnpm' : 'npm', ['run', script], { timeout: 900_000 });
    const seed = (r.out.match(/seed[:= ]+"?(\d+)/i) || [])[1]; // vitest prints: Running tests with seed "123"
    const s = seed ? ` (seed ${seed})` : '';
    return r.code === 0 ? { status: 'pass', summary: `'${script}' green in shuffled order${s}` }
      : { status: 'fail', summary: `'${script}' red in shuffled order - an order-, time- or random-dependent test${s}`, details: tail(r.out, 30) };
  }
  if (exists('pyproject.toml') || exists('pytest.ini')) {
    const r = sh('python', ['-m', 'pytest', '-q', '-p', 'random_order', '--random-order'], { timeout: 900_000 });
    if (/no module named|unrecognized arguments/i.test(r.out)) return { status: 'fail', summary: 'pytest-random-order is not installed - add it to the test deps or skip with a reason in quality-gate.json' };
    return r.code === 0 ? { status: 'pass', summary: 'pytest green in random order' } : { status: 'fail', summary: 'pytest red in random order', details: tail(r.out, 30) };
  }
  return { status: 'fail', summary: `no '${script}' script - add one (e.g. "vitest run --sequence.shuffle") or skip with a reason` };
}

// slop-signals: duplication and dead code, judged against the committed baseline (never absolute).
function checkSlopSignals() {
  const dirs = CONFIG.sourceDirs.filter((d) => exists(d) && d !== 'scripts');
  if (!dirs.length) return { status: 'skip', summary: 'no source dirs' };
  const tmp = fs.mkdtempSync(path.join(osTmp(), 'qg-jscpd-'));
  const ignore = CONFIG.ignoreDirs.map((d) => `**/${d}/**`).join(',');
  sh('npx', ['--yes', `jscpd@${CONFIG.slop.jscpd}`, '--silent', '--reporters', 'json', '--output', tmp, '--ignore', ignore, ...dirs], { timeout: 300_000 });
  const dup = readJsonSafe(path.join(tmp, 'jscpd-report.json'))?.statistics?.total?.percentage;
  let knipCount = null;
  if (exists('package.json')) {
    const k = sh('npx', ['--yes', `knip@${CONFIG.slop.knip}`, '--reporter', 'json', '--no-progress', '--no-exit-code'], { timeout: 300_000 });
    try {
      const j = JSON.parse(k.stdout.slice(k.stdout.indexOf('{')));
      // Count every issue entry whatever knip's JSON shape (arrays or keyed objects per type).
      const size = (v) => (Array.isArray(v) ? v.length : v && typeof v === 'object' ? Object.keys(v).length : 0);
      knipCount = size(j.files) + (j.issues || []).reduce((n, i) => n + Object.entries(i).filter(([k]) => !['file', 'owners'].includes(k)).reduce((m, [, v]) => m + size(v), 0), 0);
    } catch { knipCount = null; }
  }
  const now = { duplicationPct: dup ?? null, knipIssues: knipCount };
  const blPath = path.join(ROOT, CONFIG.slop.baseline);
  if (UPDATE_BASELINE) { writeJson(blPath, { gate: GATE_VERSION, generated: new Date().toISOString(), ...now }); return { status: 'pass', summary: `baseline written: ${JSON.stringify(now)}` }; }
  const bl = readJsonSafe(blPath);
  if (!bl) return { status: 'fail', summary: `no ${CONFIG.slop.baseline} - run the gate once with --mode full --update-baseline and commit it`, details: [JSON.stringify(now)] };
  const issues = [];
  if (now.duplicationPct != null && bl.duplicationPct != null && now.duplicationPct > bl.duplicationPct + CONFIG.slop.duplicationTolerancePct) issues.push(`duplication ${now.duplicationPct}% > baseline ${bl.duplicationPct}% + ${CONFIG.slop.duplicationTolerancePct}pp`);
  if (now.knipIssues != null && bl.knipIssues != null && now.knipIssues > bl.knipIssues + CONFIG.slop.knipIssueTolerance) issues.push(`knip unused/unlisted ${now.knipIssues} > baseline ${bl.knipIssues}`);
  const unmeasured = Object.entries(now).filter(([, v]) => v == null).map(([k]) => k);
  if (issues.length) return { status: 'fail', summary: issues.join('; '), details: ['Shrink it back, or (a deliberate decision) lower nothing and re-baseline with a reason in the commit body.'] };
  // A tool that did not produce a number did not check anything (Rule 383 s2).
  if (unmeasured.length) return { status: 'fail', summary: `NOT CHECKED: ${unmeasured.join(', ')} produced no measurement (jscpd/knip failed to run) - fix the tool run or skip the check with a reason` };
  return { status: 'pass', summary:`duplication ${now.duplicationPct}% (bl ${bl.duplicationPct}%), knip ${now.knipIssues} (bl ${bl.knipIssues})${unmeasured.length ? `; not measured: ${unmeasured.join(',')}` : ''}` };
}

function checkPerfBudget() {
  const p = CONFIG.perf;
  if (!p.jsBudgetKb && !p.lighthouse) return { status: 'skip', summary: 'no perf budget declared in quality-gate.json' };
  const out = []; let failed = false;
  if (p.jsBudgetKb) {
    const dir = path.join(ROOT, p.chunksDir);
    // Locally the build runs inside the Docker runner, so the host has no chunks: that is NOT CHECKED,
    // reported as WARN (never PASS); /prerelease G5 then takes the CI run's verdict as the evidence.
    if (!fs.existsSync(dir)) return { status: IN_CI ? 'fail' : 'warn', summary: `NOT CHECKED: ${p.chunksDir} missing - build first (the CI workflow builds before this check)` };
    const kb = Math.round(walk(dir).filter((f) => f.endsWith('.js')).reduce((n, f) => n + fs.statSync(f).size, 0) / 1024);
    const ok = kb <= p.jsBudgetKb; failed ||= !ok;
    out.push(`JS chunks ${kb} KB / budget ${p.jsBudgetKb} KB ${ok ? 'OK' : 'OVER'}`);
  }
  if (p.lighthouse) {
    const r = sh('npx', ['--yes', `@lhci/cli@${p.lighthouse.version || '0.16.0'}`, 'autorun', `--config=${p.lighthouse.config || 'lighthouserc.json'}`], { timeout: 900_000 });
    failed ||= r.code !== 0; out.push(`lighthouse ${r.code === 0 ? 'assertions passed' : 'assertions FAILED'}`);
    if (r.code !== 0) out.push(...tail(r.out, 20));
  }
  return { status: failed ? 'fail' : 'pass', summary: out[0], details: out.slice(1) };
}

function checkEvals() {
  if (!CONFIG.evals?.command) return { status: 'skip', summary: 'no LLM eval suite declared (quality-gate.json evals.command)' };
  // Deterministic by contract: the suite reads these and must pin temperature/seed.
  return runCommandCheck(CONFIG.evals.command, { LLM_TEMPERATURE: '0', QG_SEED: '42', ...(CONFIG.evals.env || {}) });
}

function runCommandCheck(command, env = {}) {
  const r = sh(process.platform === 'win32' ? 'cmd' : 'sh', process.platform === 'win32' ? ['/d', '/s', '/c', command] : ['-c', command], { timeout: 900_000, env });
  return r.code === 0 ? { status: 'pass', summary: `'${command}' passed` } : { status: 'fail', summary: `'${command}' exit ${r.code}`, details: tail(r.out, 25) };
}

// ═════════════════════════════════════════════════════════════════════════════
// Helpers
// ═════════════════════════════════════════════════════════════════════════════

function findRoot(start) {
  let d = start;
  for (;;) {
    if (fs.existsSync(path.join(d, 'quality-gate.json'))) return d;
    const up = path.dirname(d);
    if (up === d) return start;
    d = up;
  }
}

function loadConfig() {
  const user = fs.existsSync(CFG_PATH) ? readJsonSafe(CFG_PATH) : {};
  if (user === null) die(2, `quality-gate.json is not valid JSON`);
  const known = new Set([...Object.keys(DEFAULTS), '$schema', 'gateVersion', 'product']);
  const unknown = Object.keys(user).filter((k) => !known.has(k));
  if (unknown.length) die(2, `quality-gate.json: unknown key(s) ${unknown.join(', ')}`);
  for (const s of user.skip || []) {
    if (!s.check || !s.reason || s.reason.trim().length < 10) die(2, `quality-gate.json: every skip needs {check, reason>=10 chars} - got ${JSON.stringify(s)}`);
  }
  const merged = { ...DEFAULTS };
  for (const [k, v] of Object.entries(user)) {
    merged[k] = v && typeof v === 'object' && !Array.isArray(v) && DEFAULTS[k] && typeof DEFAULTS[k] === 'object' && !Array.isArray(DEFAULTS[k]) ? { ...DEFAULTS[k], ...v } : v;
  }
  return merged;
}

function git(args) { const r = sh('git', args, { timeout: 60_000 }); return r.code === 0 ? r.stdout : null; }

function resolveBase() {
  const head = (git(['rev-parse', 'HEAD']) || '').trim();
  const explicit = arg('base') || process.env.QG_BASE;
  if (explicit && !/^0+$/.test(explicit) && git(['rev-parse', '--verify', `${explicit}^{commit}`])) return { ref: explicit, label: explicit, head, kind: 'range' };
  if (MODE === 'quick') return { ref: 'HEAD', label: 'the index (staged)', head, kind: 'staged' };
  if (MODE === 'preclose') {
    const dirty = (git(['status', '--porcelain', '--untracked-files=normal']) || '').trim();
    if (dirty) return { ref: 'HEAD', label: 'HEAD (working tree)', head, kind: 'worktree' };
  }
  const parent = git(['rev-parse', '--verify', 'HEAD~1']);
  return parent ? { ref: 'HEAD~1', label: 'HEAD~1', head, kind: 'range' } : { ref: 'HEAD', label: 'HEAD', head, kind: 'worktree' };
}

function loadDiff() {
  const args = ['diff', '-U0', '--no-color', '--no-ext-diff', '--relative'];
  if (BASE.kind === 'staged') args.push('--cached');
  else if (BASE.kind === 'range') args.push(BASE.ref);
  else args.push('HEAD');
  const text = git(args) || '';
  const files = []; let cur = null; let n = 0;
  for (const raw of text.split('\n')) {
    if (raw.startsWith('diff --git')) { cur = null; continue; }
    if (raw.startsWith('+++ ')) {
      const p = raw.slice(4).trim();
      if (p === '/dev/null') { cur = null; continue; }
      cur = { path: p.replace(/^b\//, ''), added: [], deleted: false }; files.push(cur); continue;
    }
    if (raw.startsWith('--- ')) continue;
    const h = raw.match(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (h) { n = Number(h[1]); continue; }
    if (cur && raw.startsWith('+')) { cur.added.push({ n, text: raw.slice(1) }); n++; }
  }
  if (BASE.kind === 'worktree') {
    for (const u of (git(['ls-files', '--others', '--exclude-standard']) || '').split('\n').filter(Boolean)) {
      try {
        const body = fs.readFileSync(path.join(ROOT, u), 'utf8');
        if (body.length > 2_000_000) continue;
        files.push({ path: u, added: body.split('\n').map((t, i) => ({ n: i + 1, text: t })), deleted: false });
      } catch { /* binary or vanished */ }
    }
  }
  return { files: files.filter((f) => !CONFIG.ignoreDirs.some((d) => f.path.split('/').includes(d))) };
}

function changedDeps(before, now) {
  const out = [];
  for (const section of ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies']) {
    const a = before?.[section] || {}; const b = now?.[section] || {};
    for (const [name, spec] of Object.entries(b)) if (a[name] !== spec) out.push([name, String(spec), section]);
  }
  return out;
}

function isExactNpmSpec(spec) {
  if (/^(?:workspace|file|link|catalog|portal):/.test(spec)) return true;
  const s = spec.startsWith('npm:') ? spec.replace(/^npm:.+@/, '') : spec;
  return /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/.test(s);
}

async function fetchJson(url) {
  try {
    const ctl = AbortSignal.timeout(8000);
    const r = await fetch(url, { signal: ctl, headers: { accept: 'application/json', 'user-agent': 'quality-gate' } });
    if (r.status === 404) return { notFound: true };
    if (!r.ok) return { error: `HTTP ${r.status}` };
    return { json: await r.json() };
  } catch (e) { return { error: e.name === 'TimeoutError' ? 'timeout' : e.message }; }
}

const unverified = (what, err) => ({ level: MODE === 'full' ? 'fail' : 'warn', msg: `${what} UNVERIFIED (${err})` });

async function verifyNpm(name, version = null) {
  const meta = await fetchJson(`https://registry.npmjs.org/${name.replace('/', '%2F')}`);
  if (meta.notFound) return { level: 'fail', msg: 'NOT ON THE NPM REGISTRY - hallucinated package name?' };
  if (meta.error) return unverified('registry lookup', meta.error);
  const days = (iso) => (Date.now() - new Date(iso).getTime()) / 864e5;
  const created = meta.json.time?.created;
  if (created && days(created) < CONFIG.deps.minAgeDays) return { level: 'fail', msg: `registered ${days(created).toFixed(1)} days ago (< ${CONFIG.deps.minAgeDays}) - slopsquat risk` };
  // The VERSION's age, not only the package's: a hijacked maintainer publishes a fresh malicious
  // version of an old, popular package, and the package-created date would wave it through.
  if (version) {
    const published = meta.json.time?.[version];
    if (!published) return { level: 'fail', msg: `version ${version} is not on the registry` };
    if (days(published) < CONFIG.deps.minAgeDays) return { level: 'fail', msg: `version ${version} was published ${days(published).toFixed(1)} days ago (< ${CONFIG.deps.minAgeDays}) - wait, or pin the previous version` };
  }
  const dl = await fetchJson(`https://api.npmjs.org/downloads/point/last-week/${name}`);
  if (dl.error) return unverified('download count', dl.error);
  const n = dl.json?.downloads ?? 0;
  if (n < CONFIG.deps.minWeeklyDownloads) return { level: 'fail', msg: `${n} downloads last week (< ${CONFIG.deps.minWeeklyDownloads}) - low-trust package` };
  return { level: 'ok' };
}

async function verifyPypi(name) {
  const meta = await fetchJson(`https://pypi.org/pypi/${encodeURIComponent(name)}/json`);
  if (meta.notFound) return { level: 'fail', msg: 'NOT ON PYPI - hallucinated package name?' };
  if (meta.error) return unverified('PyPI lookup', meta.error);
  const times = Object.values(meta.json.releases || {}).flat().map((f) => new Date(f.upload_time_iso_8601 || f.upload_time)).filter((d) => !isNaN(d));
  const first = times.length ? Math.min(...times) : null;
  if (first && (Date.now() - first) / 864e5 < CONFIG.deps.minAgeDays) return { level: 'fail', msg: `first release under ${CONFIG.deps.minAgeDays} days old - slopsquat risk` };
  return { level: 'ok' };
}

function declaredNodeDeps() {
  // The product's package.json, plus the enclosing workspace roots (a micro product inherits
  // the monorepo root's devDependencies). The walk stops at the first parent that is not a
  // workspace root, so a standalone product never reads the meta-repo's manifest.
  const set = new Set(); let found = false; let d = ROOT;
  for (let i = 0; i < 4; i++) {
    const pj = readJsonSafe(path.join(d, 'package.json'));
    if (pj) {
      found = true; if (pj.name) set.add(pj.name);
      for (const s of ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies']) Object.keys(pj[s] || {}).forEach((k) => set.add(k));
    }
    const up = path.dirname(d); if (up === d) break;
    if (!fs.existsSync(path.join(up, 'pnpm-workspace.yaml')) && !fs.existsSync(path.join(up, 'turbo.json'))) break;
    d = up;
  }
  // PLUS every manifest inside the product. A monorepo product (ps: a Next.js app in
  // apps/frontend, an admin portal in apps/admin-portal) declares its real
  // dependencies in the PER-APP manifests; the product-root one carries only
  // the workspace glue. Without this union every app import was reported as
  // "hallucinated or transitive-only" and the check was RED on every commit
  // (measured 2026-11-23 on ps).
  for (const pj of findManifests('package.json')) {
    const j = readJsonSafe(pj); if (!j) continue;
    found = true; if (j.name) set.add(j.name);
    for (const s of ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies']) Object.keys(j[s] || {}).forEach((k) => set.add(k));
  }
  return found ? set : null;
}

function tsPathAliases() {
  const out = new Set(['~', '@/']);
  for (const f of ['tsconfig.json', 'jsconfig.json']) {
    try {
      const raw = fs.readFileSync(path.join(ROOT, f), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').replace(/,(\s*[}\]])/g, '$1');
      Object.keys(JSON.parse(raw).compilerOptions?.paths || {}).forEach((k) => out.add(k.replace(/\*$/, '')));
    } catch { /* no tsconfig or exotic syntax */ }
  }
  return [...out].filter(Boolean);
}

function importSpecifiers(src) {
  const code = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"`])\/\/.*$/gm, '$1');
  const re = /(?:^|[\s;])(?:import|export)\s+(?:type\s+)?(?:[^'"`;]*?\sfrom\s*)?['"]([^'"]+)['"]|\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)|\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
  const out = new Set(); let m;
  while ((m = re.exec(code))) out.add(m[1] || m[2] || m[3]);
  return out;
}

function listSourceFiles() {
  return CONFIG.sourceDirs.filter((d) => exists(d)).flatMap((d) => walk(path.join(ROOT, d)))
    .map((f) => path.relative(ROOT, f).replaceAll('\\', '/'));
}

function walk(dir) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (CONFIG.ignoreDirs.includes(e.name) || e.name.startsWith('.git')) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p)); else out.push(p);
  }
  return out;
}

function findManifests(matcher) {
  const names = []; const test = (n) => (typeof matcher === 'string' ? n === matcher : matcher.test(n));
  // A MONOREPO product declares its dependencies in the PER-APP manifests
  // (ps: apps/frontend/package.json, apps/admin-portal/package.json), not in
  // the product-root one — the root package.json only carries the workspace
  // glue. A root-only walk therefore reported every app import as
  // "hallucinated or transitive-only" (measured 2026-11-23 on ps: 8 false
  // positives on a single commit). The walk is bounded in depth and skips
  // the directories that never hold a manifest.
  const SKIP = new Set(['node_modules', '.git', '.next', 'dist', 'build', 'coverage', '.venv', 'venv', '__pycache__', '.turbo', '.output']);
  const walk = (dir, depth) => {
    if (depth > 4) return;
    let entries = [];
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const full = path.join(dir, e.name);
      if (e.isFile()) { if (test(e.name)) names.push(full); continue; }
      if (!e.isDirectory() || SKIP.has(e.name) || e.name.startsWith('.')) continue;
      walk(full, depth + 1);
    }
  };
  walk(ROOT, 0);
  return names;
}

function pickSemgrepRunner() {
  const want = process.env.QG_SEMGREP || CONFIG.sast.runner;
  const dockerOk = () => sh('docker', ['info', '--format', '{{.ServerVersion}}'], { timeout: 20_000 }).code === 0;
  const cliOk = () => sh('semgrep', ['--version'], { timeout: 30_000 }).code === 0;
  if (want === 'docker') return dockerOk() ? 'docker' : null;
  if (want === 'cli') return cliOk() ? 'cli' : null;
  // auto: the pinned image first (Rule 287 parity), the CLI only as a fallback (e.g. a CI runner without docker)
  return dockerOk() ? 'docker' : cliOk() ? 'cli' : null;
}

function gateRelPath(p) {
  const dir = path.relative(ROOT, path.dirname(fileURLToPath(import.meta.url))).replaceAll('\\', '/');
  return `${dir || '.'}/${p}`;
}
function isGateFile(p) { return /(?:^|\/)scripts\/quality-gate\/|^templates\/quality-gate\/|^\.quality-gate\/|^quality-gate\.json$/.test(p); }

function sh(cmd, args, { timeout = 120_000, env = {}, onTimeout } = {}) {
  const isWin = process.platform === 'win32';
  const r = spawnSync(cmd, args, { cwd: ROOT, encoding: 'utf8', timeout, maxBuffer: 256 * 1024 * 1024, shell: isWin && ['pnpm', 'npm', 'npx'].includes(cmd), env: { ...process.env, ...env } });
  // A timed-out spawn does NOT kill the child: the process is orphaned and
  // keeps running (measured 2026-11-23 - a 900 s semgrep timeout left a
  // 2.28 GB container scanning the tree, and the next run competed with it).
  // The caller supplies the cleanup for a resource it named.
  if (onTimeout && r.error && /ETIMEDOUT/i.test(`${r.error.code || ''} ${r.error.message || ''}`)) { try { onTimeout(); } catch { /* best effort */ } }
  return { code: r.status, stdout: r.stdout || '', out: `${r.stdout || ''}\n${r.stderr || ''}${r.error ? `\n${r.error.message}` : ''}` };
}

function res(id, status, summary) { return { id, status, summary, ms: 0 }; }
function exists(p) { return fs.existsSync(path.join(ROOT, p)); }
function readJson(p) { return JSON.parse(fs.readFileSync(p, 'utf8')); }
function readJsonSafe(p) { try { return readJson(p); } catch { return null; } }
function readJsonAt(ref, rel) { const t = git(['show', `${ref}:${rel}`]); try { return t ? JSON.parse(t) : {}; } catch { return {}; } }
function writeJson(p, o) { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, `${JSON.stringify(o, null, 2)}\n`); }
function sha(s) { return createHash('sha256').update(s).digest('hex').slice(0, 16); }
function tail(s, n = 15) { return String(s).trim().split('\n').slice(-n); }
function osTmp() { return process.env.RUNNER_TEMP || process.env.TEMP || process.env.TMPDIR || '/tmp'; }
function die(code, msg) { console.error(`[quality-gate] ${msg}`); process.exit(code); }

function report() {
  const failed = results.filter((r) => r.status === 'fail');
  const out = { gate: GATE_VERSION, mode: MODE, root: ROOT, base: BASE.label, ok: failed.length === 0, seconds: Math.round((Date.now() - started) / 100) / 10, results };
  if (JSON_OUT) { console.log(JSON.stringify(out)); }
  else {
    const icon = { pass: 'PASS', fail: 'FAIL', warn: 'WARN', skip: 'SKIP' };
    console.log(`[quality-gate] v${GATE_VERSION} mode=${MODE} base=${BASE.label}`);
    for (const r of results) {
      console.log(`  ${icon[r.status].padEnd(4)} ${r.id.padEnd(16)} ${r.summary}${r.ms ? ` (${(r.ms / 1000).toFixed(1)}s)` : ''}`);
      if (r.details?.length && r.status !== 'pass') for (const d of r.details.slice(0, 25)) console.log(`         ${d}`);
    }
    console.log(`[quality-gate] ${out.ok ? 'GREEN' : `RED - ${failed.map((f) => f.id).join(', ')}`} in ${out.seconds}s`);
  }
  if (process.env.GITHUB_STEP_SUMMARY) {
    const rows = results.map((r) => `| ${r.status} | ${r.id} | ${String(r.summary).replaceAll('|', '/')} |`).join('\n');
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `### Quality gate (${MODE})\n\n| status | check | summary |\n|---|---|---|\n${rows}\n`);
  }
  process.exit(out.ok ? 0 : 1);
}
