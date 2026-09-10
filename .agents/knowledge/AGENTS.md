# Development Knowledge

> **Role:** development-agent instructions for the development knowledge base in this directory. Not product behavior.

For the development coding agent only: maintain stable conventions and source references with provenance. Do not place product knowledge here if it must ship to users; explicitly review and place that content in the target product runtime instead.

Machine-specific facts — the contents of `development-machine-facts.md` and the rendered `.agents/local/DevelopmentMachine.md` — are device-local by design. In a public repository keep only the neutral skeleton; never commit endpoint, model, host, or smoke-evidence observations.
