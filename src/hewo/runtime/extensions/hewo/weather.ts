/**
 * HeWo product payload: weather lookup with a deterministic in-file fixture and
 * a strictly opt-in live path.
 *
 * Security posture: fixture mode is the default and performs no network I/O and
 * reads no clock, so the same input yields byte-identical output forever. Live
 * mode requires HEWO_WEATHER_MODE=live plus the weather-live capability plus
 * HEWO_NETWORK=allow plus a single allowlisted host, is HTTPS-only and timeout-
 * bounded, and degrades to the fixture on any failure. Error reasons are fixed
 * strings: no URL query, no header, and no response body ever reaches them.
 */

import type { EnvLike } from './policy.ts';
import { checkNetwork } from './policy.ts';

export type WeatherMode = 'fixture' | 'live';

export type WeatherReason =
  | 'fixture'
  | 'fixture-unknown-location'
  | 'live'
  | 'live-mode-not-selected'
  | 'live-network-refused'
  | 'live-host-unset'
  | 'live-host-invalid'
  | 'live-fetch-unavailable'
  | 'live-timeout'
  | 'live-aborted'
  | 'live-transport-error'
  | 'live-http-error'
  | 'live-unparseable-body';

export interface WeatherResult {
  /** Location exactly as requested. */
  location: string;
  /** Normalized lookup key used against the fixture table. */
  normalized: string;
  temperatureC: number | null;
  condition: string;
  observedAt: string;
  mode: WeatherMode;
  degraded: boolean;
  reason: WeatherReason;
  known: boolean;
}

interface FixtureEntry {
  temperatureC: number;
  condition: string;
  observedAt: string;
}

/**
 * Frozen fixture table. These values are the product's deterministic contract:
 * changing a row changes acceptance output, so treat edits as a behavior change.
 */
const FIXTURES: Readonly<Record<string, FixtureEntry>> = Object.freeze({
  'beijing': { temperatureC: 21, condition: 'clear', observedAt: '2026-01-01T08:00:00Z' },
  'shanghai': { temperatureC: 24, condition: 'cloudy', observedAt: '2026-01-01T08:00:00Z' },
  'shenzhen': { temperatureC: 28, condition: 'humid', observedAt: '2026-01-01T08:00:00Z' },
  'hangzhou': { temperatureC: 23, condition: 'light-rain', observedAt: '2026-01-01T08:00:00Z' },
  'hong-kong': { temperatureC: 27, condition: 'cloudy', observedAt: '2026-01-01T08:00:00Z' },
  'tokyo': { temperatureC: 19, condition: 'clear', observedAt: '2026-01-01T08:00:00Z' },
  'singapore': { temperatureC: 30, condition: 'thunderstorm', observedAt: '2026-01-01T08:00:00Z' },
  'london': { temperatureC: 12, condition: 'overcast', observedAt: '2026-01-01T08:00:00Z' },
  'new-york': { temperatureC: 15, condition: 'windy', observedAt: '2026-01-01T08:00:00Z' },
  'san-francisco': { temperatureC: 16, condition: 'fog', observedAt: '2026-01-01T08:00:00Z' },
});

export const DEFAULT_LOCATION: string = 'beijing';
export const DEFAULT_TIMEOUT_MS: number = 5000;

export function knownLocations(): string[] {
  return Object.keys(FIXTURES).slice().sort();
}

/** Lowercase, trim, and collapse any run of separators into a single hyphen. */
export function normalizeLocation(location: string): string {
  return location
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '');
}

function env(source?: EnvLike): EnvLike {
  return source ?? (process.env as EnvLike);
}

export function readWeatherMode(source?: EnvLike): WeatherMode {
  return env(source).HEWO_WEATHER_MODE === 'live' ? 'live' : 'fixture';
}

export function readTimeoutMs(source?: EnvLike): number {
  const raw = env(source).HEWO_WEATHER_TIMEOUT_MS;
  if (typeof raw !== 'string' || raw.trim() === '') return DEFAULT_TIMEOUT_MS;
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return DEFAULT_TIMEOUT_MS;
  return parsed;
}

/** An unknown location is a labelled result, never an exception. */
function fixtureResult(location: string, mode: WeatherMode, reason: WeatherReason): WeatherResult {
  const normalized = normalizeLocation(location);
  const entry = FIXTURES[normalized];
  if (entry === undefined) {
    return {
      location,
      normalized,
      temperatureC: null,
      condition: 'unknown-location',
      observedAt: 'unknown',
      mode,
      degraded: mode === 'live',
      reason: mode === 'live' ? reason : 'fixture-unknown-location',
      known: false,
    };
  }
  return {
    location,
    normalized,
    temperatureC: entry.temperatureC,
    condition: entry.condition,
    observedAt: entry.observedAt,
    mode,
    degraded: mode === 'live',
    reason: mode === 'live' ? reason : 'fixture',
    known: true,
  };
}

/** Synchronous, network-free, clock-free lookup. */
export function getFixtureWeather(location: string): WeatherResult {
  return fixtureResult(location, 'fixture', 'fixture');
}

function degraded(location: string, reason: WeatherReason): WeatherResult {
  const base = fixtureResult(location, 'live', reason);
  return { ...base, degraded: true, reason };
}

/** The host must be a bare hostname with an optional port and nothing else. */
function isValidHost(host: string): boolean {
  if (host.trim() === '') return false;
  if (/[\s/@?#\\]/.test(host)) return false;
  if (host.includes(':') && !/^[A-Za-z0-9.-]+:[0-9]{1,5}$/.test(host)) return false;
  if (!host.includes(':') && !/^[A-Za-z0-9.-]+$/.test(host)) return false;
  return true;
}

interface MinimalResponse {
  ok: boolean;
  status: number;
  text: () => Promise<string>;
}

type FetchLike = (
  url: string,
  init: { signal: AbortSignal; redirect: 'error'; method: 'GET' },
) => Promise<MinimalResponse>;

function resolveFetch(): FetchLike | undefined {
  const candidate = (globalThis as { fetch?: unknown }).fetch;
  if (typeof candidate !== 'function') return undefined;
  return candidate as FetchLike;
}

function readNumber(source: Record<string, unknown>, keys: readonly string[]): number | undefined {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string') {
      const parsed = Number.parseFloat(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return undefined;
}

function readString(source: Record<string, unknown>, keys: readonly string[]): string | undefined {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'string' && value.trim() !== '') return value.trim();
  }
  return undefined;
}

function parseLiveBody(body: string, location: string): WeatherResult | undefined {
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return undefined;
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) return undefined;
  const record = parsed as Record<string, unknown>;
  const nested = record.current;
  const scope =
    nested !== null && typeof nested === 'object' && !Array.isArray(nested)
      ? (nested as Record<string, unknown>)
      : record;

  const temperatureC = readNumber(scope, ['temperatureC', 'temperature_c', 'temperature', 'temp_c']);
  if (temperatureC === undefined) return undefined;
  const condition = readString(scope, ['condition', 'summary', 'weather', 'description']);
  if (condition === undefined) return undefined;
  const observedAt = readString(scope, ['observedAt', 'observed_at', 'time', 'timestamp']);
  if (observedAt === undefined) return undefined;

  return {
    location,
    normalized: normalizeLocation(location),
    temperatureC,
    condition,
    observedAt,
    mode: 'live',
    degraded: false,
    reason: 'live',
    known: true,
  };
}

export interface GetWeatherOptions {
  env?: EnvLike;
  signal?: AbortSignal;
}

/**
 * Fixture by default. Live only when every gate opens, and any live failure
 * degrades to the fixture result with `degraded: true` and a fixed reason code
 * rather than propagating an error to the caller.
 */
export async function getWeather(
  location: string,
  options?: GetWeatherOptions,
): Promise<WeatherResult> {
  const source = options?.env;
  const requested = typeof location === 'string' && location.trim() !== '' ? location : DEFAULT_LOCATION;

  if (readWeatherMode(source) !== 'live') {
    return getFixtureWeather(requested);
  }

  const network = checkNetwork('weather-live', source);
  if (!network.allowed) {
    return degraded(requested, 'live-network-refused');
  }

  const host = env(source).HEWO_WEATHER_ALLOWED_HOST;
  if (typeof host !== 'string' || host.trim() === '') {
    return degraded(requested, 'live-host-unset');
  }
  if (!isValidHost(host.trim())) {
    return degraded(requested, 'live-host-invalid');
  }

  const doFetch = resolveFetch();
  if (doFetch === undefined) {
    return degraded(requested, 'live-fetch-unavailable');
  }

  // HTTPS only, single allowlisted host, fixed path shape.
  const url = `https://${host.trim()}/v1/current?location=${encodeURIComponent(
    normalizeLocation(requested),
  )}`;

  const controller = new AbortController();
  const timeoutMs = readTimeoutMs(source);
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  if (typeof (timer as { unref?: () => void }).unref === 'function') {
    (timer as { unref: () => void }).unref();
  }

  const outer = options?.signal;
  const onOuterAbort = (): void => controller.abort();
  if (outer !== undefined) {
    if (outer.aborted) controller.abort();
    else outer.addEventListener('abort', onOuterAbort, { once: true });
  }

  try {
    const response = await doFetch(url, { signal: controller.signal, redirect: 'error', method: 'GET' });
    if (!response.ok) {
      return degraded(requested, 'live-http-error');
    }
    const body = await response.text();
    const parsedResult = parseLiveBody(body, requested);
    if (parsedResult === undefined) {
      return degraded(requested, 'live-unparseable-body');
    }
    return parsedResult;
  } catch {
    // Deliberately discards the thrown value: it can echo the URL or headers.
    if (timedOut) return degraded(requested, 'live-timeout');
    if (outer !== undefined && outer.aborted) return degraded(requested, 'live-aborted');
    return degraded(requested, 'live-transport-error');
  } finally {
    clearTimeout(timer);
    if (outer !== undefined) outer.removeEventListener('abort', onOuterAbort);
  }
}

/** One-line, secret-free human summary. */
export function summarizeWeather(result: WeatherResult): string {
  const temperature = result.temperatureC === null ? 'unknown' : `${result.temperatureC}C`;
  const suffix = result.degraded ? ` (degraded: ${result.reason})` : '';
  return `${result.normalized || result.location}: ${temperature}, ${result.condition}, observed ${result.observedAt} [${result.mode}]${suffix}`;
}
