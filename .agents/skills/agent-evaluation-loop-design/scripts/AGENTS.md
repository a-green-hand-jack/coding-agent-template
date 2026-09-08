# Agent Evaluation Loop Design Scripts

> **Role:** development-agent instructions for the agent-evaluation-loop-design skill's helper scripts. Not product behavior.

Deterministic, standard-library-only helpers. Rules for maintaining them:

- Never call a provider, read credentials, or perform network access.
- Never write into any `src/<agent_name>/runtime/` path.
- Same inputs must produce byte-identical outputs.
- Exit codes are a public contract; see `../references/evaluation-contract.md`.
- `compare-evaluations.py` must never promote a candidate to current best.
