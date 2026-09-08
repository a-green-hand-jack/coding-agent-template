# HeWo Extensions

For the development coding agent only: maintain the runtime extension that
exposes the product tool surface. Exclude this development guidance from
releases.

The extension provides the `hewo_time`, `hewo_weather`, and `hewo_report`
tools and the `/hewo-report` command, and it loads the sub-agent definitions
under `agents/`. Keep that surface minimal and deterministic.

Weather must default to the offline fixture mode. Live mode stays opt-in, and
a live failure must degrade to the fixture result and mark the result as
degraded. Never place credentials or host-specific configuration here.
