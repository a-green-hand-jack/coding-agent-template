# Time and Weather Workflow

1. Read the location supplied by the user, or use the configured default.
2. Choose an orchestration shape: single, parallel, or chain.
3. Report the location actually used and the weather data mode.
4. Do not claim tools, files, or external actions that did not occur.

## Single

Run one sub-agent. Use `time-reporter` for a time-only request and
`weather-reporter` for a weather-only request. Return its result directly.

## Parallel

Run `time-reporter` and `weather-reporter` at the same time, subject to the
concurrency cap. Merge the results in input order, not completion order, so
the same request always produces the same ordering.

## Chain

Run one sub-agent and pass its output as the input to the next. Use this when
the second report depends on the first, such as resolving a location before
asking for its weather. A failed step ends the chain; report the step that
failed.

## Execution guarantees

Each sub-agent runs as an independent process with its own minimal read-only
tool allowlist. A sub-agent does not inherit the parent's permissions or
session.

Results are subject to a wall-clock timeout, a concurrency cap, a retry cap,
and output truncation. Report a timed-out, retry-exhausted, or truncated
result as incomplete. Never fill in the missing part yourself.

Weather runs in deterministic fixture mode by default and needs no network.
Live mode is opt-in. A live failure degrades to the fixture result; say so,
and never present a degraded result as a live observation.
