# HeWo Themes

> **Role:** development-agent instructions for hewo's shipped theme. Not product behavior, and excluded from every payload.

For the development coding agent only: maintain the shipped theme. Exclude
this development guidance from releases.

`hewo.json` is deliberately partial: it defines a unique `name` and shared
`vars` only, and relies on pi's built-in theme for every colour token it does
not define. Do not invent token names to fill the gap. A complete theme
requires pi's full set of 53 colour tokens; add them only from a verified
token list.

Theme `name` must be unique and must not contain `/`.
