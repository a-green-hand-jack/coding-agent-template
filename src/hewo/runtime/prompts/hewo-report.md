---
description: Report the current time and the weather, with the data mode stated.
argument-hint: [location]
---

Produce the time-and-weather report for `$ARGUMENTS`.

If no location was supplied, use the runtime's configured default location.

Follow the `time-and-weather` skill. Check the tool result before reporting.
Name the location actually used, give the time with its timezone, and state
the weather data mode: `fixture` or `live`.

If a live lookup failed and the result degraded to fixture data, say so and
report the answer as fixture data.
