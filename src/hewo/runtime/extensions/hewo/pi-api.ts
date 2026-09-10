/**
 * HeWo product payload: structural type surface for the pi extension API.
 *
 * These types mirror the subset of pi 0.85.1's extension API that this runtime
 * relies on. They are STRUCTURAL DECLARATIONS, not imported from pi, because the
 * pi package is not installable in this tree; nothing here is verified by a
 * compiler against pi, so every member is optional and must be probed at runtime,
 * and this file must be re-checked whenever the pi version changes.
 *
 * Security posture: types only. No I/O, no environment access, no secrets.
 */

/** A single JSON Schema property, restricted to the shapes this runtime emits. */
export interface JsonSchemaProperty {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'object' | 'array';
  description?: string;
  enum?: readonly string[];
  default?: string | number | boolean;
  items?: JsonSchemaProperty;
}

/** The object-typed input schema every tool in this runtime declares. */
export interface JsonSchemaObject {
  type: 'object';
  properties: Record<string, JsonSchemaProperty>;
  required?: readonly string[];
  additionalProperties?: boolean;
}

/** Opaque per-call context. pi may pass more than this; treat it as read-only. */
export interface ToolCallContext {
  signal?: AbortSignal;
  sessionId?: string;
}

export type ToolHandler = (
  input: Record<string, unknown>,
  context?: ToolCallContext,
) => Promise<unknown> | unknown;

/**
 * pi returns tool output as content blocks plus opaque details. Verified
 * against pi 0.85.1 docs/extensions.md: the schema field is `parameters`
 * (a TypeBox/JSON-Schema object) and the entry point is `execute`, not
 * `handler`. Naming it `inputSchema` makes pi throw while reading
 * `parameters.properties`.
 */
export interface ToolResult {
  content: Array<{ type: 'text'; text: string }>;
  details?: Record<string, unknown>;
}

export type ToolExecute = (
  toolCallId: string,
  params: Record<string, unknown>,
  signal?: AbortSignal,
  onUpdate?: (update: unknown) => void,
  ctx?: unknown,
) => Promise<ToolResult> | ToolResult;

export interface ToolSpec {
  name: string;
  label?: string;
  description: string;
  parameters: JsonSchemaObject;
  execute: ToolExecute;
}

export type CommandHandler = (
  argument: string,
  context?: ToolCallContext,
) => Promise<unknown> | unknown;

export interface CommandSpec {
  description: string;
  handler: CommandHandler;
}

/** Lifecycle events this runtime subscribes to. Others may exist; ignore them. */
export type ExtensionEventName = 'session_start' | 'tool_call';

export interface BeforeAgentStartEvent {
  systemPrompt: string;
}

export interface SessionStartEvent {
  sessionId?: string;
  cwd?: string;
}

export interface ToolCallEvent {
  toolName?: string;
  name?: string;
  input?: Record<string, unknown>;
}

/**
 * A hook may return nothing (observe only) or a decision object (intercept).
 * pi's official tool_call refusal shape is `block: true`.
 */
export interface HookDecision {
  block: boolean;
  reason?: string;
  code?: string;
}

export type EventHandler = (
  event: SessionStartEvent | ToolCallEvent,
) => Promise<HookDecision | void> | HookDecision | void;

/**
 * Session-state accessor. pi exposes in-process, non-persisted state; the exact
 * member name is not guaranteed here, so both a property and a getter are
 * modelled and the extension probes for whichever exists.
 */
export interface SessionStateAccessor {
  get?: (key: string) => unknown;
  set?: (key: string, value: unknown) => void;
}

export interface ExtensionAPI {
  registerTool?: (spec: ToolSpec) => unknown;
  registerCommand?: (name: string, spec: CommandSpec) => unknown;
  on: {
    (event: ExtensionEventName, handler: EventHandler): unknown;
    (event: 'before_agent_start', handler: (event: BeforeAgentStartEvent) => { systemPrompt: string }): unknown;
  };
  getActiveTools(): string[];
  setActiveTools(names: string[]): void;
  sessionState?: SessionStateAccessor;
  getSessionState?: () => SessionStateAccessor | Record<string, unknown> | undefined;
  log?: (message: string) => void;
}

/** An extension module default-exports this factory; sync or async both load. */
export type ExtensionFactory = (api: ExtensionAPI) => Promise<void> | void;
