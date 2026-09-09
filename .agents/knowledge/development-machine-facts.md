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

This public repository ships only the neutral skeleton below. Real machine
facts are personal — provider endpoints, observed models, host names and smoke
evidence identify one machine and its operator — so a filled-in file must stay
device-local and must never be committed to a public repository. Fill the
fence with your own machine's metadata before regenerating
`DevelopmentMachine.md`; the renderer treats every empty section as absent.

The `render-profile.py` script reads the first ```json fence below. Keep prose
outside the fence for the human operator; the fence itself is the machine input.

```json
{
  "credential_surface": {},
  "evidence_status": [],
  "services": {},
  "notes": "Fill per machine, device-locally. Never commit endpoints, model observations, host names, or smoke evidence to a public repository."
}
```

Facts are operator-confirmed metadata from prior runtime observations. Re-verify smoke evidence after agent/model changes; live trial receipts are kept outside the repository. Endpoints, env-var names, and auth-file paths are metadata only — never key values.