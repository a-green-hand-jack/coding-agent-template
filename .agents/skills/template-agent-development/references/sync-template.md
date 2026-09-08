# Sub-skill: Synchronize Template Updates

Use this sub-skill when a downstream Agent repository derives from this
template and needs a newer template change. Synchronization is selective and
registry-driven: a downstream repository must never copy `.agents/` wholesale.

## 1. Read the registry before touching files

From the template checkout, read
`.agents/template-content-registry.json`. It is the authoritative inventory of
every tracked path in the repository: template-only content, reusable content,
reference examples, and neutral placeholders that may be installed
downstream. Every copied path must have an explicit registry entry and a review
decision. The registry covers more than `.agents/`: it also governs source
scaffolds, Docker, distribution, scripts, package metadata, CI, benchmarks,
release artifacts, and documentation.

The classes have these meanings:

- `template-only`: never copy; this includes template issue evidence, HeWo
  history, template registry/AGENTS files, and template benchmark context.
- `selective`: copy only the named implementation after adapting the listed
  names, paths, providers, and evidence commands.
- `placeholder-only`: copy only the listed neutral placeholder into the
  downstream directory; do not copy the template's current memory, knowledge,
  or workflow content.
- `downstream-owned`: create and maintain independently in the downstream
  repository.
- `template-only-or-adapt`: use as a reference and rewrite manually; never
  overwrite downstream identity or policy wholesale.

Confirm that the inventory still covers the complete template before syncing:

```bash
python3 scripts/check-template-registry.py
```

This check uses `git ls-files`, so adding a new tracked file without assigning
it a registry pattern fails instead of silently making it part of an
unreviewed downstream sync.

## 2. Establish the upstream relationship

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

## 3. Bootstrap downstream-owned directories

The template supplies neutral placeholders so a new downstream repository has
the expected development layout without inheriting template history:

```bash
template_root=/path/to/coding-agent-template
mkdir -p .agents/knowledge .agents/memory .agents/workflows
cp "$template_root/.agents/downstream-skeleton/knowledge/PLACEHOLDER.md" \
  .agents/knowledge/PLACEHOLDER.md
cp "$template_root/.agents/downstream-skeleton/memory/PLACEHOLDER.md" \
  .agents/memory/PLACEHOLDER.md
cp "$template_root/.agents/downstream-skeleton/workflows/PLACEHOLDER.md" \
  .agents/workflows/PLACEHOLDER.md
```

Replace or remove each placeholder before recording real downstream content.
Write new scoped `AGENTS.md` files for the downstream repository; never copy
the template's `.agents/**/AGENTS.md` files.

## 4. Select implementation skills individually

Opt in to only the skills the downstream development team needs. For example:

```bash
cp -R "$template_root/.agents/skills/agent-consistency-audit" .agents/skills/
cp -R "$template_root/.agents/skills/agent-definition-validation" .agents/skills/
cp -R "$template_root/.agents/skills/agent-infrastructure-health" .agents/skills/
```

`template-agent-development` is also selectable when the downstream team will
continue to synchronize or migrate using this template. After copying any
skill, adapt its registry-listed assumptions: Agent names and paths, backend
binaries, provider-backed E2E commands, release commands, and evidence issue.
Review frontmatter and linked references before committing. Do not copy the
template skill directory's `AGENTS.md` into the downstream repository.

The current `.agents/knowledge/`, `.agents/memory/`, and `.agents/workflows/`
directories are not source material for downstream installation. They contain
template maintenance context and must be replaced with downstream-owned
content, starting from the placeholders above.

## 5. Apply registered repository updates narrowly

If the repositories share history, compare both sides and choose a normal
merge or reviewed cherry-picks of template commits:

```bash
git log --oneline HEAD..template/main
git diff HEAD..template/main -- .dockerignore .env.example .github .opencode \
  distribution docker package.json pyproject.toml scripts src
```

If the downstream repository was copied without shared history, compare the
same registry-approved paths against an upstream checkout and apply a focused
patch. Never recursively replace `.agents/`, `src/`, benchmarks, release
artifacts, or CI. The inventory's broad patterns are an audit boundary, not a
permission to overwrite a downstream repository wholesale.

After applying changes:

- update stale template URLs or command names in downstream docs;
- keep `runtime/package.json` valid; a non-pi backend configuration file must
  not exist, and `validate-definition.sh` rejects one;
- preserve independent scaffold/backend/provider layering;
- review launchers, Docker, installers, and tool environments for credential
  exposure and runtime `PATH` behavior;
- treat `src/hewo/` as a renamed reference scaffold, not as a product to ship
  unchanged;
- treat `.opencode/`, `.github/`, root docs, and root package metadata as
  development/repository policy that requires manual adaptation;
- record the selected registry entries and adaptations in the downstream PR or
  issue, not in the template's historical memory.

## 6. Revalidate the downstream Agent

Run the definition check for the downstream Agent:

```bash
./scripts/validate-definition.sh <agent_name>
```

Run the consistency audit after copying or adapting development resources:

```bash
python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py \
  --agent <agent_name> --strict
```

If template infrastructure changed, rebuild the clean image and run a real
provider-backed Docker E2E through the current helper. Exercise each changed
backend/provider boundary; use read-only auth mounts or runtime environment
injection and record only scrubbed evidence. Do not call an image build a
successful Agent test.

When release behavior changed, inspect a fresh archive:

```bash
./scripts/build-release.sh <agent_name> <version>
```

Confirm development instructions, `.agents/`, credentials, and raw sessions
remain excluded. Finish with `git diff --check`, a review of the exact
registry entries applied, and a downstream-specific acceptance record.
