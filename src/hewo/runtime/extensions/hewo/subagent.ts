/**
 * HeWo product payload: sub-agent orchestration over independent `pi` child
 * processes with hard budgets.
 *
 * Security posture: every child runs with `--no-session` (never inherits or
 * writes the parent session), a minimal tool allowlist that is never empty-means-
 * everything, an explicit cwd, and an environment built by allowlist rather than
 * by copying process.env — that allowlist is the secret-isolation boundary. Wall-
 * clock timeout, output truncation, concurrency, retries, and cancellation are
 * all enforced here and reported in the result. No model client, session
 * manager, or tool loop lives in this file: pi owns all of that.
 */

import * as child_process from 'node:child_process';
import * as crypto from 'node:crypto';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import type { EnvLike, PolicyDecision } from './policy.ts';
import { decide } from './policy.ts';

export const DEFAULT_TIMEOUT_MS: number = 120000;
export const DEFAULT_MAX_CONCURRENCY: number = 2;
export const DEFAULT_MAX_RETRIES: number = 1;
export const DEFAULT_MAX_OUTPUT_BYTES: number = 65536;
export const DEFAULT_KILL_GRACE_MS: number = 2000;
export const DEFAULT_TOOLS: string = 'read';
export const DEFAULT_PI_BIN: string = 'pi';

/** Above this size the system prompt goes to a temp file instead of argv. */
const INLINE_PROMPT_LIMIT = 8000;

export interface AgentDefinition {
  name: string;
  description: string;
  tools: string[];
  promptFile?: string;
  /** Frontmatter body, or the contents of `prompt-file` when one is declared. */
  body: string;
  sourcePath: string;
}

export interface SubagentRecord {
  agent: string;
  task: string;
  exitCode: number | null;
  signal: string | null;
  durationMs: number;
  stdout: string;
  stderr: string;
  truncated: boolean;
  timedOut: boolean;
  aborted: boolean;
  retries: number;
  refused: boolean;
  refusalCode: string | null;
  refusalReason: string | null;
  spawnError: string | null;
  cleanupErrors: string[];
  ok: boolean;
}

export interface SubagentRunResult {
  /** Ordered by input order, never by completion order. */
  records: SubagentRecord[];
  merged: string;
  ok: boolean;
}

export interface SubagentOptions {
  env?: EnvLike;
  signal?: AbortSignal;
  /** Child working directory. Defaults to process.cwd(). */
  cwd?: string;
}

export interface ChainStep {
  agent: string;
  /** Optional instruction prefixed to the previous step's output. */
  task?: string;
}

function env(source?: EnvLike): EnvLike {
  return source ?? (process.env as EnvLike);
}

function readInt(source: EnvLike, key: string, fallback: number): number {
  const raw = source[key];
  if (typeof raw !== 'string' || raw.trim() === '') return fallback;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
}

function readString(source: EnvLike, key: string, fallback: string): string {
  const raw = source[key];
  if (typeof raw !== 'string' || raw.trim() === '') return fallback;
  return raw.trim();
}

/**
 * Locates `src/hewo/runtime/agents/` from this file's own directory: two levels
 * up (extensions/hewo -> extensions -> runtime) then `agents`.
 */
function extensionDir(): string {
  const meta = import.meta as { dirname?: string; url?: string };
  if (typeof meta.dirname === 'string' && meta.dirname !== '') return meta.dirname;
  const url = typeof meta.url === 'string' ? meta.url : '';
  const raw = url.startsWith('file://') ? url.slice('file://'.length) : url;
  return path.dirname(decodeURIComponent(raw));
}

export function agentsDirectory(source?: EnvLike): string {
  // The runtime manifest declares agent_definitions and the launcher resolves
  // and exports it, so that path is authoritative. Deriving the location from
  // this module's own path is only a fallback: under the backend's TypeScript
  // loader the module path does not reliably resolve back to the payload.
  const declared = env(source).HEWO_AGENT_DEFINITIONS;
  if (typeof declared === 'string' && declared.trim() !== '') {
    return path.resolve(declared.trim());
  }
  return path.resolve(extensionDir(), '..', '..', 'agents');
}

function isSafeName(name: string): boolean {
  if (typeof name !== 'string' || name.trim() === '') return false;
  if (name.includes('\0')) return false;
  if (name.includes('/') || name.includes('\\')) return false;
  if (name === '.' || name === '..') return false;
  if (path.isAbsolute(name)) return false;
  return /^[A-Za-z0-9._-]+$/.test(name);
}

function isInside(root: string, candidate: string): boolean {
  if (candidate === root) return true;
  return candidate.startsWith(root.endsWith(path.sep) ? root : root + path.sep);
}

/** Minimal `key: value` frontmatter reader. No YAML library, by design. */
export function parseFrontmatter(text: string): {
  keys: Record<string, string>;
  body: string;
} {
  const normalized = text.replace(/\r\n/g, '\n');
  const lines = normalized.split('\n');
  if (lines[0]?.trim() !== '---') {
    return { keys: {}, body: normalized.trim() };
  }
  const keys: Record<string, string> = {};
  let index = 1;
  let closed = false;
  for (; index < lines.length; index += 1) {
    const line = lines[index] ?? '';
    if (line.trim() === '---') {
      closed = true;
      index += 1;
      break;
    }
    const separator = line.indexOf(':');
    if (separator <= 0) continue;
    const key = line.slice(0, separator).trim().toLowerCase();
    let value = line.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"') && value.length >= 2) ||
      (value.startsWith("'") && value.endsWith("'") && value.length >= 2)
    ) {
      value = value.slice(1, -1);
    }
    if (key !== '') keys[key] = value;
  }
  if (!closed) return { keys: {}, body: normalized.trim() };
  return { keys, body: lines.slice(index).join('\n').trim() };
}

function parseToolList(raw: string | undefined): string[] {
  if (typeof raw !== 'string' || raw.trim() === '') return [];
  const out: string[] = [];
  for (const part of raw.split(',')) {
    const tool = part.trim();
    if (tool !== '' && /^[A-Za-z0-9_-]+$/.test(tool) && !out.includes(tool)) out.push(tool);
  }
  return out;
}

export function loadAgentDefinition(name: string): AgentDefinition {
  if (!isSafeName(name)) {
    throw new Error(`invalid agent name: ${JSON.stringify(name)}`);
  }
  const root = agentsDirectory();
  const file = path.resolve(root, `${name}.md`);
  if (!isInside(root, file)) {
    throw new Error('agent definition resolves outside the agents directory');
  }
  const text = fs.readFileSync(file, 'utf8');
  const parsed = parseFrontmatter(text);

  let body = parsed.body;
  const promptFile = parsed.keys['prompt-file'];
  if (typeof promptFile === 'string' && promptFile !== '') {
    if (promptFile.includes('\0') || promptFile.includes('..') || path.isAbsolute(promptFile)) {
      throw new Error('prompt-file must be a safe relative path');
    }
    const resolved = path.resolve(root, promptFile);
    if (!isInside(root, resolved)) {
      throw new Error('prompt-file resolves outside the agents directory');
    }
    body = fs.readFileSync(resolved, 'utf8').replace(/\r\n/g, '\n').trim();
  }

  return {
    name: parsed.keys['name'] ?? name,
    description: parsed.keys['description'] ?? '',
    tools: parseToolList(parsed.keys['tools']),
    promptFile: typeof promptFile === 'string' && promptFile !== '' ? promptFile : undefined,
    body,
    sourcePath: file,
  };
}

export function listAgentDefinitions(): AgentDefinition[] {
  const root = agentsDirectory();
  let entries: string[];
  try {
    entries = fs.readdirSync(root);
  } catch {
    return [];
  }
  const out: AgentDefinition[] = [];
  for (const entry of entries.slice().sort()) {
    if (!entry.endsWith('.md')) continue;
    // AGENTS.md files are development instructions, never product
    // resources. Loading one as a sub-agent definition would hand the
    // product agent this repository's maintenance instructions.
    if (entry === 'AGENTS.md') continue;
    const name = entry.slice(0, -3);
    if (!isSafeName(name)) continue;
    try {
      out.push(loadAgentDefinition(name));
    } catch {
      // A malformed definition is skipped, not fatal for the rest.
    }
  }
  return out;
}

/**
 * Definition tools intersected with HEWO_SUBAGENT_TOOLS. An empty intersection
 * must never be read as "all tools", so the caller passes --no-tools instead.
 */
export function resolveToolAllowlist(definitionTools: string[], source?: EnvLike): string[] {
  const permitted = parseToolList(readString(env(source), 'HEWO_SUBAGENT_TOOLS', DEFAULT_TOOLS));
  const requested = definitionTools.length === 0 ? parseToolList(DEFAULT_TOOLS) : definitionTools;
  const out: string[] = [];
  for (const tool of requested) {
    if (permitted.includes(tool) && !out.includes(tool)) out.push(tool);
  }
  return out;
}

/**
 * Child environment is assembled from an allowlist. process.env is never copied,
 * so provider credentials only reach a child when an operator names them in
 * HEWO_SUBAGENT_ENV_PASSTHROUGH. Values are never logged.
 */
export function buildChildEnv(source?: EnvLike): Record<string, string> {
  const parent = env(source);
  const out: Record<string, string> = {};
  for (const key of ['PATH', 'HOME', 'PI_CODING_AGENT_DIR']) {
    const value = parent[key];
    if (typeof value === 'string') out[key] = value;
  }
  for (const key of Object.keys(parent)) {
    if (!key.startsWith('HEWO_')) continue;
    const value = parent[key];
    if (typeof value === 'string') out[key] = value;
  }
  const extra = parent.HEWO_SUBAGENT_ENV_PASSTHROUGH;
  if (typeof extra === 'string') {
    for (const part of extra.split(',')) {
      const key = part.trim();
      if (key === '' || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue;
      const value = parent[key];
      if (typeof value === 'string') out[key] = value;
    }
  }
  return out;
}

export function buildChildArgs(
  definition: AgentDefinition,
  task: string,
  promptArgument: string,
  source?: EnvLike,
): string[] {
  const parent = env(source);
  // --no-session is mandatory and non-overridable: a sub-agent must never
  // inherit or write the parent session.
  const args: string[] = ['--no-session', '--print'];

  const tools = resolveToolAllowlist(definition.tools, source);
  if (tools.length === 0) args.push('--no-tools');
  else args.push('--tools', tools.join(','));

  args.push('--append-system-prompt', promptArgument);

  const provider = parent.HEWO_PROVIDER;
  if (typeof provider === 'string' && provider.trim() !== '') {
    args.push('--provider', provider.trim());
  }
  const model = parent.HEWO_MODEL;
  if (typeof model === 'string' && model.trim() !== '') {
    args.push('--model', model.trim());
  }

  // Turn budget: pi 0.85.1 exposes no --max-turns flag, so a per-turn cap is an
  // unenforceable-by-CLI backend capability gap. Wall-clock timeout and output
  // truncation below are the substitutes; do not invent a flag for this.
  args.push('--', task);
  return args;
}

class Semaphore {
  limit: number;
  active: number;
  waiters: Array<() => void>;

  constructor(limit: number) {
    this.limit = limit > 0 ? limit : 1;
    this.active = 0;
    this.waiters = [];
  }

  async acquire(): Promise<void> {
    if (this.active < this.limit) {
      this.active += 1;
      return;
    }
    await new Promise<void>((resolve) => {
      this.waiters.push(resolve);
    });
    this.active += 1;
  }

  release(): void {
    if (this.active > 0) this.active -= 1;
    const next = this.waiters.shift();
    if (next !== undefined) next();
  }
}

class ByteCollector {
  chunks: Buffer[];
  total: number;
  limit: number;
  truncated: boolean;

  constructor(limit: number) {
    this.chunks = [];
    this.total = 0;
    this.limit = limit;
    this.truncated = false;
  }

  push(chunk: Buffer): void {
    if (this.total >= this.limit) {
      this.truncated = true;
      return;
    }
    const room = this.limit - this.total;
    if (chunk.length <= room) {
      this.chunks.push(chunk);
      this.total += chunk.length;
      return;
    }
    this.chunks.push(chunk.subarray(0, room));
    this.total += room;
    this.truncated = true;
  }

  text(): string {
    const joined = Buffer.concat(this.chunks).toString('utf8');
    return this.truncated ? `${joined}\n[hewo: output truncated]` : joined;
  }
}

interface AttemptOutcome {
  exitCode: number | null;
  signal: string | null;
  stdout: string;
  stderr: string;
  truncated: boolean;
  timedOut: boolean;
  aborted: boolean;
  spawnError: string | null;
  cleanupErrors: string[];
}

/** SIGTERM the whole process group, then SIGKILL it after the grace period. */
function killGroup(pid: number | undefined, signal: NodeJS.Signals): void {
  if (pid === undefined) return;
  try {
    process.kill(-pid, signal);
  } catch {
    try {
      process.kill(pid, signal);
    } catch {
      // Already gone.
    }
  }
}

function writePromptFile(body: string, cleanupErrors: string[]): { argument: string; cleanup: () => void } {
  if (body.length <= INLINE_PROMPT_LIMIT) {
    return { argument: body, cleanup: () => undefined };
  }
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hewo-subagent-'));
  const file = path.join(dir, `${crypto.randomUUID()}.md`);
  fs.writeFileSync(file, body, { encoding: 'utf8', mode: 0o600 });
  const cleanup = (): void => {
    try {
      fs.rmSync(dir, { recursive: true, force: true });
    } catch (error) {
      cleanupErrors.push(`temp prompt cleanup failed: ${describeError(error)}`);
    }
  };
  return { argument: file, cleanup };
}

function describeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'unknown error';
}

async function runAttempt(
  definition: AgentDefinition,
  task: string,
  options: SubagentOptions,
): Promise<AttemptOutcome> {
  const source = env(options.env);
  const cleanupErrors: string[] = [];
  const timeoutMs = readInt(source, 'HEWO_SUBAGENT_TIMEOUT_MS', DEFAULT_TIMEOUT_MS);
  const graceMs = readInt(source, 'HEWO_SUBAGENT_KILL_GRACE_MS', DEFAULT_KILL_GRACE_MS);
  const maxBytes = readInt(source, 'HEWO_SUBAGENT_MAX_OUTPUT_BYTES', DEFAULT_MAX_OUTPUT_BYTES);
  const bin = readString(source, 'HEWO_PI_BIN', DEFAULT_PI_BIN);
  const cwd = options.cwd ?? process.cwd();

  const prompt = writePromptFile(definition.body, cleanupErrors);
  const args = buildChildArgs(definition, task, prompt.argument, source);

  const stdout = new ByteCollector(maxBytes);
  const stderr = new ByteCollector(maxBytes);

  let timedOut = false;
  let aborted = false;
  let spawnError: string | null = null;
  let killTimer: NodeJS.Timeout | undefined;
  let timeoutTimer: NodeJS.Timeout | undefined;
  const signal = options.signal;
  let onAbort: (() => void) | undefined;

  try {
    const child = child_process.spawn(bin, args, {
      cwd,
      env: buildChildEnv(source),
      // detached so the timeout can kill the whole process group, not just pi.
      detached: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    child.stdout?.on('data', (chunk: Buffer) => stdout.push(chunk));
    child.stderr?.on('data', (chunk: Buffer) => stderr.push(chunk));

    const escalate = (): void => {
      killGroup(child.pid, 'SIGTERM');
      killTimer = setTimeout(() => killGroup(child.pid, 'SIGKILL'), graceMs);
      if (typeof killTimer.unref === 'function') killTimer.unref();
    };

    timeoutTimer = setTimeout(() => {
      timedOut = true;
      escalate();
    }, timeoutMs);
    if (typeof timeoutTimer.unref === 'function') timeoutTimer.unref();

    if (signal !== undefined) {
      onAbort = (): void => {
        aborted = true;
        escalate();
      };
      if (signal.aborted) onAbort();
      else signal.addEventListener('abort', onAbort, { once: true });
    }

    const outcome = await new Promise<{ code: number | null; signalName: string | null }>(
      (resolve) => {
        child.once('error', (error: Error) => {
          spawnError = describeError(error);
          resolve({ code: null, signalName: null });
        });
        child.once('close', (code: number | null, closeSignal: NodeJS.Signals | null) => {
          resolve({ code, signalName: closeSignal === null ? null : String(closeSignal) });
        });
      },
    );

    return {
      exitCode: outcome.code,
      signal: outcome.signalName,
      stdout: stdout.text(),
      stderr: stderr.text(),
      truncated: stdout.truncated || stderr.truncated,
      timedOut,
      aborted,
      spawnError,
      cleanupErrors,
    };
  } catch (error) {
    return {
      exitCode: null,
      signal: null,
      stdout: stdout.text(),
      stderr: stderr.text(),
      truncated: stdout.truncated || stderr.truncated,
      timedOut,
      aborted,
      spawnError: describeError(error),
      cleanupErrors,
    };
  } finally {
    if (timeoutTimer !== undefined) clearTimeout(timeoutTimer);
    if (killTimer !== undefined) clearTimeout(killTimer);
    if (signal !== undefined && onAbort !== undefined) {
      signal.removeEventListener('abort', onAbort);
    }
    prompt.cleanup();
  }
}

function refusedRecord(agent: string, task: string, decision: PolicyDecision): SubagentRecord {
  return {
    agent,
    task,
    exitCode: null,
    signal: null,
    durationMs: 0,
    stdout: '',
    stderr: '',
    truncated: false,
    timedOut: false,
    aborted: false,
    retries: 0,
    refused: true,
    refusalCode: decision.code,
    refusalReason: decision.reason,
    spawnError: null,
    cleanupErrors: [],
    ok: false,
  };
}

function errorRecord(agent: string, task: string, message: string): SubagentRecord {
  return {
    agent,
    task,
    exitCode: null,
    signal: null,
    durationMs: 0,
    stdout: '',
    stderr: '',
    truncated: false,
    timedOut: false,
    aborted: false,
    retries: 0,
    refused: false,
    refusalCode: null,
    refusalReason: null,
    spawnError: message,
    cleanupErrors: [],
    ok: false,
  };
}

/** Retry only on a spawn failure or a timeout, never on a task-level refusal. */
function shouldRetry(outcome: AttemptOutcome): boolean {
  if (outcome.aborted) return false;
  if (outcome.spawnError !== null) return true;
  if (outcome.timedOut) return true;
  return false;
}

async function runOne(
  agent: string,
  task: string,
  options: SubagentOptions,
): Promise<SubagentRecord> {
  const source = env(options.env);
  const gate = decide({ capability: 'subagent' }, source);
  if (!gate.allowed) return refusedRecord(agent, task, gate);

  let definition: AgentDefinition;
  try {
    definition = loadAgentDefinition(agent);
  } catch (error) {
    return errorRecord(agent, task, describeError(error));
  }

  const maxRetries = readInt(source, 'HEWO_SUBAGENT_MAX_RETRIES', DEFAULT_MAX_RETRIES);
  const started = Date.now();
  let retries = 0;
  let outcome = await runAttempt(definition, task, options);
  while (shouldRetry(outcome) && retries < maxRetries) {
    retries += 1;
    const next = await runAttempt(definition, task, options);
    next.cleanupErrors = outcome.cleanupErrors.concat(next.cleanupErrors);
    outcome = next;
  }

  return {
    agent: definition.name,
    task,
    exitCode: outcome.exitCode,
    signal: outcome.signal,
    durationMs: Date.now() - started,
    stdout: outcome.stdout,
    stderr: outcome.stderr,
    truncated: outcome.truncated,
    timedOut: outcome.timedOut,
    aborted: outcome.aborted,
    retries,
    refused: false,
    refusalCode: null,
    refusalReason: null,
    spawnError: outcome.spawnError,
    cleanupErrors: outcome.cleanupErrors,
    ok:
      outcome.spawnError === null &&
      !outcome.timedOut &&
      !outcome.aborted &&
      outcome.exitCode === 0,
  };
}

function mergeRecords(records: SubagentRecord[]): string {
  const parts: string[] = [];
  for (const record of records) {
    const header = `## ${record.agent}`;
    if (record.refused) {
      parts.push(`${header}\n[refused: ${record.refusalCode}] ${record.refusalReason ?? ''}`.trim());
      continue;
    }
    if (!record.ok) {
      const cause = record.spawnError ?? (record.timedOut ? 'timeout' : `exit ${String(record.exitCode)}`);
      parts.push(`${header}\n[failed: ${cause}]`);
      continue;
    }
    parts.push(`${header}\n${record.stdout.trim()}`);
  }
  return parts.join('\n\n');
}

export async function runSingle(
  agent: string,
  task: string,
  options?: SubagentOptions,
): Promise<SubagentRunResult> {
  const record = await runOne(agent, task, options ?? {});
  return { records: [record], merged: mergeRecords([record]), ok: record.ok };
}

export interface ParallelJob {
  agent: string;
  task: string;
}

export async function runParallel(
  jobs: ParallelJob[],
  options?: SubagentOptions,
): Promise<SubagentRunResult> {
  const resolved = options ?? {};
  const source = env(resolved.env);
  const limit = readInt(source, 'HEWO_SUBAGENT_MAX_CONCURRENCY', DEFAULT_MAX_CONCURRENCY);
  const semaphore = new Semaphore(limit);

  const settled = await Promise.all(
    jobs.map(async (job) => {
      await semaphore.acquire();
      try {
        return await runOne(job.agent, job.task, resolved);
      } finally {
        semaphore.release();
      }
    }),
  );

  // `settled` preserves input order because Promise.all does, regardless of
  // which child finished first.
  const merged = mergeRecords(settled);
  let ok = true;
  for (const record of settled) {
    if (!record.ok) ok = false;
  }
  return { records: settled, merged, ok };
}

export async function runChain(
  steps: ChainStep[],
  initialTask: string,
  options?: SubagentOptions,
): Promise<SubagentRunResult> {
  const resolved = options ?? {};
  const records: SubagentRecord[] = [];
  let carried = initialTask;
  let ok = true;

  for (const step of steps) {
    if (resolved.signal?.aborted === true) {
      records.push(errorRecord(step.agent, carried, 'aborted before start'));
      ok = false;
      break;
    }
    const task =
      step.task === undefined || step.task.trim() === ''
        ? carried
        : `${step.task.trim()}\n\n${carried}`;
    const record = await runOne(step.agent, task, resolved);
    records.push(record);
    if (!record.ok) {
      ok = false;
      break;
    }
    carried = record.stdout.trim();
  }

  const last = records[records.length - 1];
  const merged = ok && last !== undefined ? last.stdout.trim() : mergeRecords(records);
  return { records, merged, ok };
}
