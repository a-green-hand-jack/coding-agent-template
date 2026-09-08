/**
 * HeWo product payload: the pi extension factory.
 *
 * Security posture: registers three typed tools, one command, and two defensive
 * lifecycle hooks. Capability gating comes from policy.ts (default deny), the
 * clock is pinned by HEWO_CLOCK_FIXED so acceptance is deterministic, and the
 * only thing ever written to the console is a single secret-free posture line.
 * The factory never throws: on any setup failure it registers nothing and says
 * once that the extension is inert.
 */

import type {
  ExtensionAPI,
  ExtensionFactory,
  SessionStartEvent,
  SessionStateAccessor,
  ToolCallEvent,
  ToolSpec,
} from './pi-api.ts';
import type { EnvLike, PolicyDecision } from './policy.ts';
import { decide, describePosture } from './policy.ts';
import type { WeatherResult } from './weather.ts';
import { DEFAULT_LOCATION, getWeather, readWeatherMode, summarizeWeather } from './weather.ts';

const STATE_KEY = 'hewo.toolInvocations';

/** RFC 3339 date-time, with a required offset or Z. */
const RFC3339 =
  /^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$/;

export interface TimeResult {
  now: string;
  fixed: boolean;
  source: 'HEWO_CLOCK_FIXED' | 'system';
}

export interface ReportResult {
  time: TimeResult;
  weather: WeatherResult;
  summary: string;
}

function env(source?: EnvLike): EnvLike {
  return source ?? (process.env as EnvLike);
}

/**
 * Clock rule: a valid HEWO_CLOCK_FIXED is returned verbatim so fixture
 * acceptance never reads the ambient clock. An invalid value is ignored rather
 * than treated as fatal.
 */
export function getTime(source?: EnvLike): TimeResult {
  const raw = env(source).HEWO_CLOCK_FIXED;
  if (typeof raw === 'string' && RFC3339.test(raw.trim())) {
    return { now: raw.trim(), fixed: true, source: 'HEWO_CLOCK_FIXED' };
  }
  return { now: new Date().toISOString(), fixed: false, source: 'system' };
}

function defaultLocation(source?: EnvLike): string {
  const configured = env(source).HEWO_WEATHER_LOCATION;
  if (typeof configured === 'string' && configured.trim() !== '') return configured.trim();
  return DEFAULT_LOCATION;
}

function readLocationInput(input: Record<string, unknown> | undefined, source?: EnvLike): string {
  const candidate = input?.location;
  if (typeof candidate === 'string' && candidate.trim() !== '') return candidate.trim();
  return defaultLocation(source);
}

/** The composed product task: current time plus weather for one location. */
export async function buildReport(
  location: string,
  options?: { env?: EnvLike; signal?: AbortSignal },
): Promise<ReportResult> {
  const source = options?.env;
  const time = getTime(source);
  const weather = await getWeather(location, { env: source, signal: options?.signal });
  const summary = `As of ${time.now}${time.fixed ? ' (fixed clock)' : ''}, ${summarizeWeather(weather)}.`;
  return { time, weather, summary };
}

/** Maps a tool name to the capability its current configuration requires. */
export function capabilityForTool(toolName: string, source?: EnvLike): string | undefined {
  if (toolName === 'hewo_weather' || toolName === 'hewo_report') {
    return readWeatherMode(source) === 'live' ? 'weather-live' : undefined;
  }
  if (toolName.startsWith('hewo_subagent')) return 'subagent';
  if (toolName === 'write' || toolName === 'edit') return 'workspace-write';
  return undefined;
}

function resolveSessionState(api: ExtensionAPI): SessionStateAccessor | undefined {
  if (api.sessionState !== undefined) return api.sessionState;
  if (typeof api.getSessionState !== 'function') return undefined;
  try {
    const state = api.getSessionState();
    if (state === undefined || state === null) return undefined;
    const candidate = state as SessionStateAccessor;
    if (typeof candidate.get === 'function' || typeof candidate.set === 'function') {
      return candidate;
    }
    // A plain record: adapt it to the accessor shape without persisting anything.
    const record = state as Record<string, unknown>;
    return {
      get: (key: string) => record[key],
      set: (key: string, value: unknown) => {
        record[key] = value;
      },
    };
  } catch {
    return undefined;
  }
}

/** In-process only. Nothing here is written to disk. */
function bumpCounter(state: SessionStateAccessor | undefined): number {
  if (state === undefined) return 0;
  let current = 0;
  try {
    const stored = typeof state.get === 'function' ? state.get(STATE_KEY) : undefined;
    if (typeof stored === 'number' && Number.isFinite(stored)) current = stored;
  } catch {
    current = 0;
  }
  const next = current + 1;
  try {
    if (typeof state.set === 'function') state.set(STATE_KEY, next);
  } catch {
    // State is a convenience, never a requirement.
  }
  return next;
}

function emit(api: ExtensionAPI, message: string): void {
  if (typeof api.log === 'function') {
    try {
      api.log(message);
      return;
    } catch {
      // Fall through to the console.
    }
  }
  console.log(message);
}

const LOCATION_SCHEMA = {
  type: 'object' as const,
  properties: {
    location: {
      type: 'string' as const,
      description: 'Location name. Defaults to HEWO_WEATHER_LOCATION, else a fixed default.',
    },
  },
  required: [] as readonly string[],
  additionalProperties: false,
};

const EMPTY_SCHEMA = {
  type: 'object' as const,
  properties: {},
  required: [] as readonly string[],
  additionalProperties: false,
};

function buildTools(api: ExtensionAPI): ToolSpec[] {
  const state = resolveSessionState(api);

  const timeTool: ToolSpec = {
    name: 'hewo_time',
    description: 'Return the current time. Pinned to HEWO_CLOCK_FIXED when that is set.',
    inputSchema: EMPTY_SCHEMA,
    handler: () => {
      const invocations = bumpCounter(state);
      return { ...getTime(), invocations };
    },
  };

  const weatherTool: ToolSpec = {
    name: 'hewo_weather',
    description: 'Return weather for a location. Deterministic fixture unless live mode is enabled.',
    inputSchema: LOCATION_SCHEMA,
    handler: async (input, context) => {
      const invocations = bumpCounter(state);
      const location = readLocationInput(input);
      const gate = gateTool('hewo_weather');
      if (!gate.allowed) return { refused: true, code: gate.code, reason: gate.reason, invocations };
      const weather = await getWeather(location, { signal: context?.signal });
      return { ...weather, invocations };
    },
  };

  const reportTool: ToolSpec = {
    name: 'hewo_report',
    description: 'Return the current time and the weather for a location as one structured report.',
    inputSchema: LOCATION_SCHEMA,
    handler: async (input, context) => {
      const invocations = bumpCounter(state);
      const location = readLocationInput(input);
      const gate = gateTool('hewo_report');
      if (!gate.allowed) return { refused: true, code: gate.code, reason: gate.reason, invocations };
      const report = await buildReport(location, { signal: context?.signal });
      return { ...report, invocations };
    },
  };

  return [timeTool, weatherTool, reportTool];
}

/** Applies policy.decide() for whatever capability the tool currently needs. */
export function gateTool(toolName: string, source?: EnvLike): PolicyDecision {
  const capability = capabilityForTool(toolName, source);
  if (capability === undefined) {
    return { allowed: true, reason: 'core capability', code: 'ok' };
  }
  return decide({ capability }, source);
}

function postureLine(): string {
  const posture = describePosture();
  const capabilities = posture.capabilities.length === 0 ? 'none' : posture.capabilities.join(',');
  const clock = getTime();
  return [
    'hewo: posture',
    `weather-mode=${readWeatherMode()}`,
    `network=${posture.network}`,
    `capabilities=${capabilities}`,
    `workspace=${posture.workspace}`,
    `clock=${clock.fixed ? 'fixed' : 'system'}`,
  ].join(' ');
}

function toolNameOf(event: SessionStartEvent | ToolCallEvent): string | undefined {
  const candidate = event as ToolCallEvent;
  if (typeof candidate.toolName === 'string') return candidate.toolName;
  if (typeof candidate.name === 'string') return candidate.name;
  return undefined;
}

function registerHooks(api: ExtensionAPI): void {
  if (typeof api.on !== 'function') {
    emit(api, 'hewo: lifecycle hooks unavailable on this API surface; skipping hooks');
    return;
  }

  try {
    api.on('session_start', () => {
      emit(api, postureLine());
    });
  } catch {
    emit(api, 'hewo: session_start hook could not be registered; skipping it');
  }

  try {
    api.on('tool_call', (event) => {
      const name = toolNameOf(event);
      if (name === undefined) return;
      const decision = gateTool(name);
      if (decision.allowed) return;
      return { allow: false, reason: decision.reason, code: decision.code };
    });
  } catch {
    emit(api, 'hewo: tool_call hook could not be registered; skipping it');
  }
}

const factory: ExtensionFactory = async (api: ExtensionAPI): Promise<void> => {
  try {
    if (typeof api.registerTool === 'function') {
      for (const tool of buildTools(api)) {
        api.registerTool(tool);
      }
    } else {
      emit(api, 'hewo: registerTool unavailable on this API surface; no tools registered');
    }

    if (typeof api.registerCommand === 'function') {
      api.registerCommand({
        name: 'hewo-report',
        description: 'Show the current time and the weather for the configured location.',
        handler: async (argument) => {
          const location =
            typeof argument === 'string' && argument.trim() !== ''
              ? argument.trim()
              : defaultLocation();
          const gate = gateTool('hewo_report');
          if (!gate.allowed) {
            return `hewo: refused (${gate.code}) ${gate.reason}`;
          }
          const report = await buildReport(location);
          return report.summary;
        },
      });
    } else {
      emit(api, 'hewo: registerCommand unavailable on this API surface; no command registered');
    }

    registerHooks(api);
  } catch {
    // Never throw out of the factory: an inert extension is recoverable, a
    // failed load is not.
    emit(api, 'hewo: setup failed; extension is inert and registered nothing');
  }
};

export default factory;
