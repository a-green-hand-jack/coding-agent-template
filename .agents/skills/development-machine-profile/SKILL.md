---
name: development-machine-profile
description: Capture a complete, secret-free profile of the development machine into .agents/local/DevelopmentMachine.md — host resources (OS/kernel/CPU/GPU/storage), runtime and toolchain versions, agent backends and the Harbor interface surface, plus any other available services (Lark, Hugging Face, Docker, SSH hosts, and cloud APIs such as Bohrium LKM). Use when recording or refreshing the development machine environment so a coding agent stops re-probing the host.
metadata:
  short-description: Probe and record the development machine environment
---

# Development Machine Profile

> **Role of this document**
> - **Audience:** the development coding agent recording or refreshing a repository's development-machine record.
> - **Authority:** normative. The capture pipeline, the iteration loop and the secret-safety rules are binding and never relaxed.
> - **Tone:** imperative and procedural; a probe-and-render pipeline followed by rules stated as prohibitions.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** the progressive-loading order, the one-shot probe-and-render command, how to extend the probe when it misses a capability, the secret-safety rules, and downstream use.
> - **Excludes:** the field-by-field contract (see `references/profile-schema.md`), this machine's non-probeable facts (see `.agents/knowledge/development-machine-facts.md`), and the rendered record (see `.agents/local/DevelopmentMachine.md`).

Produce (or refresh) a repository's `.agents/local/DevelopmentMachine.md`: a secret-free,
one-shot record of everything on the development machine that could affect
developing the product Agent. The skill is **generic and discovery-driven** —
it probes the host and reads each tool's own `--help` documentation, and it
must not depend on any other skill (especially user-level skills) or on
Harbor source code.

## Progressive loading

1. Read `references/profile-schema.md` for the capability-family contract and
   the hard secret-safety rules. It is the source of truth for what each
   section must contain and what is forbidden.
2. Run the probe (read-only, emits machine-profile JSON):
   ```bash
   bash .agents/skills/development-machine-profile/scripts/probe-host.sh > /tmp/machine-profile.json
   ```
3. Read the repo-local operator facts file
   `.agents/knowledge/development-machine-facts.md` (secret-free; supplies the
   non-probeable facts — provider endpoints, model observations, smoke
   evidence). If it is absent, create it from the schema in
   `references/profile-schema.md`.

## One-shot capture

From the repository root:

```bash
bash .agents/skills/development-machine-profile/scripts/probe-host.sh \
  | python3 .agents/skills/development-machine-profile/scripts/render-profile.py \
      --facts .agents/knowledge/development-machine-facts.md \
      --output .agents/local/DevelopmentMachine.md
```

The renderer merges probed facts with the operator facts file and writes
`.agents/local/DevelopmentMachine.md` deterministically (the default output path),
creating parent directories as needed. Keep this device-local file ignored and
uncommitted; ignore rules do not prohibit explicit-path reads when needed.
Re-running the same command must
regenerate the document without manual gap-filling.

## Iteration loop (keep the skill complete)

When the probe misses a capability, extend it in place — do not hand-patch the
document:

1. Diff the rendered `.agents/local/DevelopmentMachine.md` against
   `references/profile-schema.md`; every family must be non-empty.
2. Add the missing fact to the relevant family in `scripts/probe-host.sh`
   (one probe section) and, if it is a new family, one section in
   `references/profile-schema.md`.
3. Non-probeable facts (endpoints, model ids, evidence) go into
   `.agents/knowledge/development-machine-facts.md`, never into the skill.
4. Re-run the one-shot command and repeat until it is complete.

## Secret-safety rules (never relax these)

- The probe runs only read-only commands: `--version`, `--help`,
  `command -v`, OS/storage/port queries, SSH **alias** listing,
  environment-variable **existence** checks, and bare GET reachability probes
  of documented endpoints (HTTP status only, no body, no auth header).
- Never print secret values, never read key files, never run
  `opencode debug config`. Record listening services as port + process name
  only (no command lines); record SSH host aliases only (no addresses).
- Smoke command shapes use `${VAR}` expansion only; secrets are supplied by
  the operator at run time and are never written into the document.
- `.agents/local/DevelopmentMachine.md` and the facts file contain variable names,
  endpoints, file paths, and model ids — never key contents, tokens, or
  auth payloads.

## Downstream use

Downstream Agent repositories invoke this skill to generate their own
`.agents/local/DevelopmentMachine.md`. The skill itself is machine-agnostic; the
operator-maintained `.agents/knowledge/development-machine-facts.md` is
downstream-owned and holds that machine's non-probeable facts.
