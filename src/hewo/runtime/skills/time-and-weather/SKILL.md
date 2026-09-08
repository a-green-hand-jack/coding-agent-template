---
name: time-and-weather
description: Report the current time and the weather for a location, stating whether the weather came from fixture or live data.
allowed-tools: hewo_report, hewo_time, hewo_weather
---

# Time and Weather

Use this skill when the user asks for the current time, the weather, or both.

1. Prefer `hewo_report` for a combined request. Use `hewo_time` and
   `hewo_weather` when only one half is asked for.
2. Pass the location the user named. If the user named none, use the
   runtime's configured default location.
3. Check the tool result before claiming success. Never claim to have used a
   tool or produced a report without checking the result.
4. Report the location actually used, not the location requested, when the
   two differ.
5. State the weather data mode in the answer: `fixture` for the default
   deterministic data, `live` for a successful live observation.
6. A live request that fails degrades to the fixture result. Report such an
   answer as fixture data and say that the live lookup failed. Never present
   a degraded result as a live observation.
7. Report only the returned values. Do not estimate, forecast, or interpolate
   beyond what the tool returned.
8. Give the time with its timezone.
