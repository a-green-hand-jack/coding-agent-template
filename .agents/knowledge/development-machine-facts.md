# Development machine facts (operator-confirmed, secret-free)

> **Role of this document**
> - **Audience:** the development coding agent running `development-machine-profile`, and the human developer who confirms these facts.
> - **Authority:** record. Operator-confirmed observations fixed at the date they were taken; re-verify rather than rewrite.
> - **Tone:** factual and dated; metadata entries and their provenance, with no procedure and no argument.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** the non-probeable machine facts as one JSON fence: provider endpoints, environment-variable names, auth-file paths, model observations, and smoke-evidence status.
> - **Excludes:** key values, tokens and auth payloads; the field-by-field contract for these entries (see `.agents/skills/development-machine-profile/references/profile-schema.md`) and the probed, rendered profile (see `DevelopmentMachine.md`).

Supplies the non-probeable facts that the `development-machine-profile` skill
merges into `DevelopmentMachine.md`: provider endpoints, environment-variable
names, auth-file paths (metadata), model observations, and smoke-evidence
status. **Never put key values, tokens, or auth payloads here.**

The `render-profile.py` script reads the first ```json fence below. Keep prose
outside the fence for the human operator; the fence itself is the machine input.

```json
{
  "credential_surface": {
    "OpenAI-compatible Apex (codex / opencode)": {
      "env_vars": ["OPENAI_API_KEY", "OPENAI_BASE_URL"],
      "endpoint": "https://api.apexin.ai/v1",
      "auth_files": ["~/.codex/auth.json", "~/.local/share/opencode/auth.json"],
      "discovery_commands": ["opencode models <provider>", "pi --list-models"],
      "notes": "Codex and OpenCode share the OpenAI-compatible Apex endpoint. Model observations: openai/gpt-5.6-sol, openai/gpt-5.5."
    },
    "Anthropic-compatible Apex (claude-code)": {
      "env_vars": ["ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"],
      "endpoint": "https://api.apexin.ai",
      "auth_files": [],
      "discovery_commands": ["opencode models <provider>", "pi --list-models"],
      "notes": "Claude Code uses the Anthropic-compatible endpoint (no /v1 suffix). Model observation: claude-sonnet-5."
    },
    "OpenAI OAuth (codex / opencode)": {
      "env_vars": ["CODEX_AUTH_JSON_PATH"],
      "endpoint": "",
      "auth_files": ["~/.codex/auth.json"],
      "discovery_commands": [],
      "notes": "Codex OpenAI OAuth is wired through CODEX_AUTH_JSON_PATH (a direct auth.json bind-mount is recorded as failed). OpenCode OAuth needs the custom provider module plus node_modules mounts."
    }
  },
  "evidence_status": [
    {"agent": "codex", "auth_mode": "OpenAI-compatible Apex", "model": "openai/gpt-5.6-sol", "status": "smoke-verified", "note": "hello-world reward 1.0 (prior runtime observation, 2026-09-03)"},
    {"agent": "opencode", "auth_mode": "OpenAI-compatible Apex", "model": "openai/gpt-5.6-sol", "status": "smoke-verified", "note": "hello-world reward 1.0 (prior runtime observation, 2026-09-03)"},
    {"agent": "claude-code", "auth_mode": "Anthropic-compatible Apex", "model": "claude-sonnet-5", "status": "provider-reached-not-satisfied", "note": "provider calls succeeded but task-path mismatch (/hello.txt vs /app/hello.txt); not a full task success until rerun"}
  ],
  "services": {
    "Bohrium LKM": {
      "endpoint": "https://open.bohrium.com/openapi/v2/lkm",
      "env_vars": ["BOHR_ACCESS_KEY"],
      "auth_header": "Authorization: Bearer <key>",
      "documented_endpoints": ["POST /search", "POST /reasoning/search", "POST /papers/graph", "GET /claims/{id}/reasoning", "POST /variables/batch", "POST /feedback", "POST /parse/task"],
      "notes": "Bohrium Large Knowledge Model (research-knowledge API). code==0 in the JSON body is app-level success (HTTP status alone is not sufficient). Official doc: dptech-corp/bohrium-skills zh/bohrium-lkm."
    }
  },
  "notes": "Facts are operator-confirmed metadata from prior runtime observations. Re-verify smoke evidence after Harbor/agent/model changes; live trial receipts are kept outside the repository. Endpoints, env-var names, and auth-file paths are metadata only — never key values."
}
```
