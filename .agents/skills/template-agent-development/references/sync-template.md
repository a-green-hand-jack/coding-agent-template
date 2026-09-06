# Sub-skill: Synchronize Template Updates

Use this sub-skill when a downstream Agent repository already derives from the
template and needs to consume newer template infrastructure.

## 1. Establish the upstream relationship

Inspect existing remotes and history before changing anything:

```bash
git remote -v
git status --short --branch
git log --oneline --decorate -8
```

If no template remote exists, add the canonical upstream without replacing the
downstream `origin`:

```bash
git remote add template git@github.com:a-green-hand-jack/coding-agent-template.git
git fetch template --tags
```

Use the actual upstream URL configured by the project if it has moved. Work on
a dedicated branch or clean worktree. Do not discard uncommitted downstream
work, force-reset, or force-push to resolve a conflict.

## 2. Classify before applying

Treat the following as template-owned infrastructure that can usually be
updated after review:

- `distribution/`, `docker/`, and `scripts/`
- root packaging and validation configuration

Treat template-development context as non-transferable by default:

- `.agents/memory/` issue evidence and template history;
- HeWo-specific `.agents/knowledge/` and `.agents/workflows/` entries;
- template release notes, benchmark results, and CI acceptance evidence;
- template-specific README/DEV/USER wording, repository URLs, examples, and
  GitHub issue references.

Do not sync `.agents/` as a directory. Review generic skills individually and
copy only those the downstream repository still needs, adapting Agent names,
paths, helper commands, provider assumptions, and evidence destinations.
Likewise, adopt `benchmarks/` or CI definitions only when the downstream Agent
uses that contract; replace HeWo-specific tasks and verifiers rather than
presenting them as downstream evidence.

Treat these as downstream product-owned and never overwrite them wholesale:

- `src/<agent>/runtime/` identity, skills, knowledge, workflows, and tools
- `src/<agent>/development/`
- downstream product-specific `AGENTS.md`, memory, and provider policy

Files such as root `AGENTS.md`, `DEV.md`, and provider configuration may contain
both template and downstream policy. Review and merge them manually. Preserve
local security rules and credentials boundaries even when adopting upstream
examples.

## 3. Apply the smallest coherent update

If the repositories share history, compare both sides and choose a normal merge
or reviewed cherry-picks of template commits:

```bash
git log --oneline HEAD..template/main
git diff HEAD..template/main -- distribution docker scripts
```

If the downstream repository was copied without shared history, compare the
same template-owned paths against an upstream checkout and apply a focused
patch. Do not recursively replace `src/`, `.agents/`, benchmarks, or CI.

After applying changes:

- update stale template URLs or command names in downstream docs;
- keep `opencode.json` valid even when the selected backend is Codex or Claude;
- preserve the independent scaffold/backend/provider layering;
- review any launcher, Docker, installer, or tool-environment change for
  credential exposure and runtime `PATH` behavior.

## 4. Revalidate the downstream Agent

Run the definition check for the downstream Agent:

```bash
./scripts/validate-definition.sh <agent_name>
```

If template infrastructure changed, rebuild the clean image and run a real
provider-backed Docker E2E through the current helper. Exercise each changed
backend/provider boundary; use read-only auth mounts or runtime environment
injection and record only scrubbed evidence. Do not call an image build a
successful Agent test.

When release behavior changed, inspect a fresh archive:

```bash
AGENT_BACKENDS=opencode,codex,claude \
  ./scripts/build-release.sh <agent_name> <version>
```

Confirm development instructions, `.agents/`, credentials, and raw sessions
remain excluded. Finish with `git diff --check` and a review of the exact
template commits applied.
