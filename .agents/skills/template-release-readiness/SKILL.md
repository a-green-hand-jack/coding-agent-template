---
name: template-release-readiness
description: Audit this coding-agent template before release for downstream compatibility, registry coverage, template-specific leakage, and product-boundary safety.
metadata:
  short-description: Pre-release audit for downstream Agent repositories
---

# Template Release Readiness

Use this skill before publishing a new template version or tag. It evaluates
the template as a reusable development base, not only the sample `hewo`
product. It does not replace provider-backed behavior evidence.

## Release gates

Run the deterministic audit from the repository root:

```bash
python3 .agents/skills/template-release-readiness/scripts/audit_template_release.py \
  --agent hewo
```

When a release archive exists, include it:

```bash
python3 .agents/skills/template-release-readiness/scripts/audit_template_release.py \
  --agent hewo --release release/hewo-<version>.tar.gz
```

The audit checks that:

- every Git-tracked template path is classified by
  `.agents/template-content-registry.json`;
- registry entries, downstream placeholders, selectable skills, and required
  template infrastructure still exist;
- registry metadata distinguishes template-only, selective,
  template-example, and downstream-owned content;
- tracked content has no obvious credentials or retired provider variables;
- a release archive excludes development instructions, `.agents/`, registry
  data, benchmark/template history, and other template-only material.

An error blocks release. Warnings require a human review of the cited file;
they must not be hidden by deleting historical evidence.

## Complete the release gates

After the deterministic audit passes:

1. Run `agent-consistency-audit` with `--strict` for the selected Agent and
   inspect every finding.
2. Run `agent-infrastructure-health` from this exact worktree. A clean image,
   launcher check, or backend version check is infrastructure evidence only.
3. Build a fresh release with `scripts/build-release.sh`, inspect its file list,
   and rerun the audit with `--release`.
4. Run real provider-backed Docker E2E for every backend/provider combination
   promised by the template. Inject credentials only at runtime and record
   scrubbed response evidence in the normal issue/evidence location.
5. Confirm `DEV.md`, `USER.md`, the registry, and the sync sub-skill describe
   the same current commands, repository identity, backend/provider boundary,
   and downstream installation rules.

Do not publish solely because the sample Agent starts. The release must also
leave a downstream Agent developer with a safe, selectable set of skills and
neutral memory/knowledge/workflow placeholders, without inheriting template
history or credentials.
