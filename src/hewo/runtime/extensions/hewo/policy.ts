/**
 * HeWo product payload: default-deny capability, path, and network gate.
 *
 * Security posture: every non-core capability is denied unless explicitly
 * allowlisted in HEWO_CAPABILITIES; the only writable root is HEWO_WORKSPACE and
 * paths are checked lexically before they touch the filesystem; outbound network
 * is denied unless HEWO_NETWORK=allow AND the capability is allowlisted.
 * Credential-shaped paths are refused even inside the workspace. No value of any
 * environment variable other than the HEWO_* posture flags is ever logged.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

export type EnvLike = Record<string, string | undefined>;

export type CapabilityName = 'weather-live' | 'subagent' | 'workspace-write';

export const KNOWN_CAPABILITIES: readonly CapabilityName[] = [
  'weather-live',
  'subagent',
  'workspace-write',
];

export type NetworkPosture = 'deny' | 'allow';

/** Stable, machine-readable decision codes. Never renumber or reword these. */
export type PolicyCode =
  | 'ok'
  | 'capability-denied'
  | 'capability-unknown'
  | 'network-denied'
  | 'network-capability-denied'
  | 'path-empty'
  | 'path-nul-byte'
  | 'path-absolute'
  | 'path-traversal'
  | 'path-windows-prefix'
  | 'path-credential-store'
  | 'path-escapes-workspace'
  | 'path-symlink'
  | 'path-unresolvable'
  | 'workspace-unset'
  | 'workspace-unresolvable';

export interface PolicyDecision {
  allowed: boolean;
  reason: string;
  code: PolicyCode;
}

export interface PolicyRequest {
  /** Capability the action needs. Omit for a core action. */
  capability?: string;
  /** True when the action performs outbound network I/O. */
  network?: boolean;
  /** Workspace-relative path the action reads or writes. */
  path?: string;
}

/** Typed error carrying a stable `code`; parameter properties are not used
 * because this file must survive type-stripping with no transform. */
export class HewoPolicyError extends Error {
  code: PolicyCode;

  constructor(code: PolicyCode, message: string) {
    super(message);
    this.name = 'HewoPolicyError';
    this.code = code;
  }
}

function env(source?: EnvLike): EnvLike {
  return source ?? (process.env as EnvLike);
}

function allow(reason: string): PolicyDecision {
  return { allowed: true, reason, code: 'ok' };
}

function deny(code: PolicyCode, reason: string): PolicyDecision {
  return { allowed: false, reason, code };
}

/** Parsed allowlist. Unset or empty denies every non-core capability. */
export function readCapabilities(source?: EnvLike): CapabilityName[] {
  const raw = env(source).HEWO_CAPABILITIES;
  if (typeof raw !== 'string' || raw.trim() === '') return [];
  const parts = raw.split(',');
  const result: CapabilityName[] = [];
  for (const part of parts) {
    const name = part.trim();
    if (name === '') continue;
    for (const known of KNOWN_CAPABILITIES) {
      if (known === name && !result.includes(known)) result.push(known);
    }
  }
  return result;
}

export function hasCapability(capability: string, source?: EnvLike): boolean {
  const allowed = readCapabilities(source);
  for (const name of allowed) {
    if (name === capability) return true;
  }
  return false;
}

export function readNetworkPosture(source?: EnvLike): NetworkPosture {
  return env(source).HEWO_NETWORK === 'allow' ? 'allow' : 'deny';
}

export function readWorkspaceRoot(source?: EnvLike): string | undefined {
  const raw = env(source).HEWO_WORKSPACE;
  if (typeof raw !== 'string' || raw.trim() === '') return undefined;
  return raw;
}

export function checkCapability(capability: string, source?: EnvLike): PolicyDecision {
  let known = false;
  for (const name of KNOWN_CAPABILITIES) {
    if (name === capability) known = true;
  }
  if (!known) {
    return deny('capability-unknown', `capability "${capability}" is not a known HeWo capability`);
  }
  if (!hasCapability(capability, source)) {
    return deny(
      'capability-denied',
      `capability "${capability}" is not listed in HEWO_CAPABILITIES (default is deny-all)`,
    );
  }
  return allow(`capability "${capability}" is allowlisted`);
}

/**
 * Outbound network needs two independent grants: the posture flag and the
 * capability. Either one missing refuses.
 */
export function checkNetwork(capability: string, source?: EnvLike): PolicyDecision {
  if (readNetworkPosture(source) !== 'allow') {
    return deny('network-denied', 'outbound network is denied (HEWO_NETWORK is not "allow")');
  }
  const capabilityDecision = checkCapability(capability, source);
  if (!capabilityDecision.allowed) {
    return deny(
      'network-capability-denied',
      `outbound network requires capability "${capability}": ${capabilityDecision.reason}`,
    );
  }
  return allow(`outbound network allowed for capability "${capability}"`);
}

function normalizeForMatch(candidate: string): string {
  return candidate.split('\\').join('/').toLowerCase();
}

/**
 * Credential-store shapes are refused even inside the workspace, so a
 * misconfigured workspace root cannot turn into a secret read.
 */
export function looksLikeCredentialStore(candidate: string): boolean {
  const normalized = normalizeForMatch(candidate);
  const segments = normalized.split('/');
  const base = segments[segments.length - 1] ?? '';

  if (base === 'auth.json') return true;
  if (base === '.env' || base.startsWith('.env.')) return true;
  if (normalized.includes('_api_key')) return true;
  if (normalized.includes('.pi/agent/auth')) return true;

  for (const segment of segments) {
    if (segment === '') continue;
    if (segment.includes('credentials')) return true;
    if (segment === '.ssh') return true;
  }
  return false;
}

/** Lexical rejections, applied before any filesystem call. */
function checkPathLexically(relative: string): PolicyDecision {
  if (typeof relative !== 'string' || relative.trim() === '') {
    return deny('path-empty', 'path is empty');
  }
  if (relative.includes('\u0000')) {
    return deny('path-nul-byte', 'path contains a NUL byte');
  }
  // Windows shapes are checked before the absolute check so a UNC path reports
  // the precise code rather than being absorbed by the leading-separator rule.
  if (/^[A-Za-z]:/.test(relative)) {
    return deny('path-windows-prefix', 'path carries a Windows drive prefix');
  }
  if (relative.startsWith('\\\\') || relative.startsWith('//')) {
    return deny('path-windows-prefix', 'path carries a UNC prefix');
  }
  if (relative.startsWith('/') || relative.startsWith('\\')) {
    return deny('path-absolute', 'path must be workspace-relative, not absolute');
  }
  if (path.isAbsolute(relative)) {
    return deny('path-absolute', 'path must be workspace-relative, not absolute');
  }
  const segments = relative.split('\\').join('/').split('/');
  for (const segment of segments) {
    if (segment === '..') {
      return deny('path-traversal', 'path contains a ".." segment');
    }
  }
  if (looksLikeCredentialStore(relative)) {
    return deny('path-credential-store', 'path resembles a credential store');
  }
  return allow('path passes lexical checks');
}

function isInside(root: string, candidate: string): boolean {
  if (candidate === root) return true;
  return candidate.startsWith(root.endsWith(path.sep) ? root : root + path.sep);
}

/**
 * Refuses a symlink at the target or at any parent between the workspace root
 * and the target, so a link planted inside the workspace cannot redirect a write.
 */
function findSymlinkInside(root: string, target: string): string | undefined {
  const relative = path.relative(root, target);
  if (relative === '') return undefined;
  const segments = relative.split(path.sep);
  let current = root;
  for (const segment of segments) {
    if (segment === '') continue;
    current = path.join(current, segment);
    let stats: fs.Stats;
    try {
      stats = fs.lstatSync(current);
    } catch {
      // Not created yet: nothing to redirect, and deeper segments cannot exist.
      return undefined;
    }
    if (stats.isSymbolicLink()) return current;
  }
  return undefined;
}

function deepestExisting(candidate: string): string {
  let current = candidate;
  for (;;) {
    if (fs.existsSync(current)) return current;
    const parent = path.dirname(current);
    if (parent === current) return current;
    current = parent;
  }
}

export interface ResolvedWorkspacePath {
  /** Absolute path to use. Existing components are realpath-resolved. */
  absolute: string;
  /** Realpath of the workspace root the path was validated against. */
  root: string;
}

/**
 * The only sanctioned way to turn a model-supplied relative path into an
 * absolute one. Order matters: lexical rejections first, then realpath
 * containment, then the symlink sweep.
 */
export function resolveWorkspacePath(
  relative: string,
  source?: EnvLike,
): ResolvedWorkspacePath {
  const lexical = checkPathLexically(relative);
  if (!lexical.allowed) {
    throw new HewoPolicyError(lexical.code, lexical.reason);
  }

  const configured = readWorkspaceRoot(source);
  if (configured === undefined) {
    throw new HewoPolicyError('workspace-unset', 'HEWO_WORKSPACE is not set');
  }

  let root: string;
  try {
    root = fs.realpathSync(configured);
  } catch {
    throw new HewoPolicyError(
      'workspace-unresolvable',
      'HEWO_WORKSPACE does not resolve to an existing directory',
    );
  }

  const joined = path.resolve(root, relative);
  if (!isInside(root, joined)) {
    throw new HewoPolicyError('path-escapes-workspace', 'path resolves outside the workspace root');
  }

  const existing = deepestExisting(joined);
  let existingReal: string;
  try {
    existingReal = fs.realpathSync(existing);
  } catch {
    throw new HewoPolicyError('path-unresolvable', 'path could not be resolved');
  }
  if (!isInside(root, existingReal)) {
    throw new HewoPolicyError(
      'path-escapes-workspace',
      'path resolves outside the workspace root after realpath',
    );
  }

  const link = findSymlinkInside(root, joined);
  if (link !== undefined) {
    throw new HewoPolicyError(
      'path-symlink',
      'path traverses or targets a symlink inside the workspace',
    );
  }

  const suffix = path.relative(existing, joined);
  const absolute = suffix === '' ? existingReal : path.join(existingReal, suffix);
  if (!isInside(root, absolute)) {
    throw new HewoPolicyError('path-escapes-workspace', 'path resolves outside the workspace root');
  }
  if (looksLikeCredentialStore(absolute)) {
    throw new HewoPolicyError('path-credential-store', 'path resembles a credential store');
  }

  return { absolute, root };
}

export function checkWorkspacePath(relative: string, source?: EnvLike): PolicyDecision {
  try {
    const resolved = resolveWorkspacePath(relative, source);
    return allow(`path is inside the workspace root (${resolved.root})`);
  } catch (error) {
    if (error instanceof HewoPolicyError) return deny(error.code, error.message);
    return deny('path-unresolvable', 'path could not be resolved');
  }
}

/**
 * Single entry point for gating an action. Always returns a structured decision
 * so a refusal can be explained to the model and asserted in a test.
 */
export function decide(request: PolicyRequest, source?: EnvLike): PolicyDecision {
  if (request.capability !== undefined) {
    const decision = checkCapability(request.capability, source);
    if (!decision.allowed) return decision;
  }
  if (request.network === true) {
    const capability = request.capability ?? 'weather-live';
    const decision = checkNetwork(capability, source);
    if (!decision.allowed) return decision;
  }
  if (request.path !== undefined) {
    const decision = checkWorkspacePath(request.path, source);
    if (!decision.allowed) return decision;
  }
  return allow('allowed');
}

export interface PolicyPosture {
  capabilities: CapabilityName[];
  network: NetworkPosture;
  workspace: string;
}

/** Secret-free posture summary for the one operator-visible startup line. */
export function describePosture(source?: EnvLike): PolicyPosture {
  const capabilities = readCapabilities(source);
  return {
    capabilities,
    network: readNetworkPosture(source),
    workspace: readWorkspaceRoot(source) ?? '<unset>',
  };
}
