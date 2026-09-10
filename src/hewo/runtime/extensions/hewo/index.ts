/**
 * HeWo product payload: the pi extension factory.
 *
 * Security posture: registers three typed tools, one command, and two defensive
 * lifecycle hooks. Capability gating comes from policy.ts (default deny), the
 * clock is pinned by HEWO_CLOCK_FIXED so acceptance is deterministic, and the
 * only thing ever written to the console is a single secret-free posture line.
 * Runtime manifest validation happens before registration; invalid resources
 * fail extension loading instead of silently dropping the product definition.
 */

import type {
  ToolResult,
  ExtensionAPI,
  ExtensionFactory,
  SessionStartEvent,
  SessionStateAccessor,
  ToolCallEvent,
  ToolSpec,
} from './pi-api.ts';
import { loadRuntimeManifest } from './manifest.ts';
import type { EnvLike, PolicyDecision } from './policy.ts';
import { decide, describePosture } from './policy.ts';
import { listAgentDefinitions, runChain, runParallel, runSingle } from './subagent.ts';
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

const SUBAGENT_SCHEMA: ToolSpec['parameters'] = {
  type: 'object' as const,
  properties: {
    shape: {
      type: 'string',
      enum: ['single', 'parallel', 'chain'],
      description: 'Orchestration shape. single runs one sub-agent; parallel runs several concurrency-capped; chain feeds each output into the next.',
    },
    agents: {
      type: 'array',
      items: { type: 'string' },
      description: 'Sub-agent definition names. Omit to use every available definition.',
    },
    task: { type: 'string', description: 'The task text handed to the sub-agent(s).' },
  },
  required: ['shape', 'task'] as readonly string[],
  additionalProperties: false,
};

function buildTools(api: ExtensionAPI): ToolSpec[] {
  const state = resolveSessionState(api);

  // pi hands tool output back to the model as content blocks. The structured
  // payload is repeated in `details` so a caller can read it without parsing.
  const reply = (payload: Record<string, unknown>): ToolResult => ({
    content: [{ type: 'text', text: JSON.stringify(payload) }],
    details: payload,
  });

  const timeTool: ToolSpec = {
    name: 'hewo_time',
    label: 'HeWo time',
    description: 'Return the current time. Pinned to HEWO_CLOCK_FIXED when that is set.',
    parameters: EMPTY_SCHEMA,
    execute: () => {
      const invocations = bumpCounter(state);
      return reply({ ...getTime(), invocations });
    },
  };

  const weatherTool: ToolSpec = {
    name: 'hewo_weather',
    label: 'HeWo weather',
    description: 'Return weather for a location. Deterministic fixture unless live mode is enabled.',
    parameters: LOCATION_SCHEMA,
    execute: async (_toolCallId, params, signal) => {
      const invocations = bumpCounter(state);
      const location = readLocationInput(params);
      const gate = gateTool('hewo_weather');
      if (!gate.allowed) {
        return reply({ refused: true, code: gate.code, reason: gate.reason, invocations });
      }
      const weather = await getWeather(location, { signal });
      return reply({ ...weather, invocations });
    },
  };

  const reportTool: ToolSpec = {
    name: 'hewo_report',
    label: 'HeWo report',
    description: 'Return the current time and the weather for a location as one structured report.',
    parameters: LOCATION_SCHEMA,
    execute: async (_toolCallId, params, signal) => {
      const invocations = bumpCounter(state);
      const location = readLocationInput(params);
      const gate = gateTool('hewo_report');
      if (!gate.allowed) {
        return reply({ refused: true, code: gate.code, reason: gate.reason, invocations });
      }
      const report = await buildReport(location, { signal });
      return reply({ ...report, invocations });
    },
  };

  // Sub-agents are capability-gated: with HEWO_CAPABILITIES unset this tool
  // exists but every call is refused, which is the default-deny posture.
  const subagentTool: ToolSpec = {
    name: 'hewo_subagent',
    label: 'HeWo sub-agent',
    description:
      'Delegate a task to one or more read-only sub-agents. Each runs as an independent process with its own minimal tool allowlist and hard time, concurrency, retry and output budgets.',
    parameters: SUBAGENT_SCHEMA,
    execute: async (_toolCallId, params, signal) => {
      const invocations = bumpCounter(state);
      const gate = gateTool('hewo_subagent');
      if (!gate.allowed) {
        return reply({ refused: true, code: gate.code, reason: gate.reason, invocations });
      }
      const shape = typeof params.shape === 'string' ? params.shape : 'single';
      const task = typeof params.task === 'string' ? params.task : '';
      if (task.trim() === '') {
        return reply({ refused: true, code: 'task-empty', reason: 'task must not be empty', invocations });
      }
      const available = listAgentDefinitions().map((item) => item.name);
      const requested =
        Array.isArray(params.agents) && params.agents.length > 0
          ? params.agents.filter((item): item is string => typeof item === 'string')
          : available;
      const names = requested.filter((item) => available.includes(item));
      if (names.length === 0) {
        return reply({ refused: true, code: 'no-such-agent', reason: `available definitions: ${available.join(', ') || 'none'}`, invocations });
      }
      const options = { signal };
      const outcome =
        shape === 'parallel'
          ? await runParallel(names.map((agent) => ({ agent, task })), options)
          : shape === 'chain'
            ? await runChain(names.map((agent) => ({ agent })), task, options)
            : await runSingle(names[0], task, options);
      return reply({
        shape,
        agents: names,
        ok: outcome.ok,
        merged: outcome.merged,
        records: outcome.records.map((record) => ({
          agent: record.agent,
          ok: record.ok,
          exitCode: record.exitCode,
          durationMs: record.durationMs,
          timedOut: record.timedOut,
          truncated: record.truncated,
          retries: record.retries,
          refused: record.refused,
          refusalCode: record.refusalCode,
        })),
        invocations,
      });
    },
  };

  return [timeTool, weatherTool, reportTool, subagentTool];
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

function registerHooks(api: ExtensionAPI, runtime: ReturnType<typeof loadRuntimeManifest>): void {
  if (typeof api.on !== 'function') {
    emit(api, 'hewo: lifecycle hooks unavailable on this API surface; skipping hooks');
    return;
  }

  try {
    api.on('session_start', () => {
      // Intersect, never re-enable tools the user disabled with native pi flags.
      api.setActiveTools(api.getActiveTools().filter((name) => runtime.tools.has(name)));
      emit(api, postureLine());
    });
  } catch {
    emit(api, 'hewo: session_start hook could not be registered; skipping it');
  }

  try {
    api.on('tool_call', (event) => {
      const name = toolNameOf(event);
      if (name === undefined) return;
      if (!runtime.tools.has(name)) return { block: true, reason: 'Tool is not in agent.default_tools' };
      const decision = gateTool(name);
      if (decision.allowed) return;
      return { block: true, reason: decision.reason, code: decision.code };
    });
  } catch {
    emit(api, 'hewo: tool_call hook could not be registered; skipping it');
  }
}

const factory: ExtensionFactory = async (api: ExtensionAPI): Promise<void> => {
  const runtime = loadRuntimeManifest();
  api.on('before_agent_start', (event) => ({
    systemPrompt: `${event.systemPrompt}\n\n${runtime.prompt}`,
  }));
  try {
    if (typeof api.registerTool === 'function') {
      for (const tool of buildTools(api)) {
        api.registerTool(tool);
      }
    } else {
      emit(api, 'hewo: registerTool unavailable on this API surface; no tools registered');
    }

    if (typeof api.registerCommand === 'function') {
      // pi takes the command name as the first argument, not inside the spec.
      // The name must not collide with the `hewo-report` prompt template: two
      // commands answering one slash name is ambiguous, and the collision was
      // observed to make the invocation produce nothing at all. This one runs
      // the composition directly, without a model turn.
      api.registerCommand('hewo-report-direct', {
        description: 'Show the current time and weather directly, without a model turn.',
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

    registerHooks(api, runtime);
  } catch {
    // Never throw out of the factory: an inert extension is recoverable, a
    // failed load is not.
    emit(api, 'hewo: setup failed; extension is inert and registered nothing');
  }
};

export default factory;
