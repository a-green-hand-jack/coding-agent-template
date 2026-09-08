# Self-Bootstrap Protocol (advanced)

> **Role of this document**
> - **Audience:** the development coding agent optimizing this skill itself, never one optimizing a product Agent.
> - **Authority:** normative. The base-evaluator isolation, the pre-committed manifest and the accept/reject gate bind any self-bootstrap run.
> - **Tone:** precise and cautionary; the limits of the guarantee stated before the mechanism that provides it.
> - **Language:** English.
> - **Contains:** the scope of the isolation guarantee, the pre-committed candidate manifest, the check CLI, and the accept/reject state machine ending in human review.
> - **Excludes:** the normal product optimization path (see `.agents/skills/agent-evaluation-loop-design/SKILL.md`), and any claim about product performance (see `benchmarks/README.md`).

For optimizing **this skill**, not a product Agent. Do not read this to run a
normal product loop; use `SKILL.md`'s normal path.

The subject under evaluation is a candidate revision of
`.agents/skills/agent-evaluation-loop-design/`. The problem it solves: a
candidate that both changes the skill *and* changes the thing that grades the
skill can always make itself pass. So the grader comes from an immutable base
commit, never from the candidate.

## 1. Scope of the guarantee

This mechanism prevents a *normal* candidate from relaxing the evaluator,
fixtures or expected results in the same change. Git diff and output-root
checks constrain the declared repository and output boundaries only.

It is **not** an OS sandbox and does not stop arbitrary malicious code from
touching other host resources. Do not execute an untrusted, un-reviewed
candidate on the host. If you need to defend against malicious code, run it in
a read-only container sandbox — this protocol does not pretend to provide that.

## 2. Candidate manifest, pre-committed in the base

Each candidate declares its hypothesis *before* implementation, in the **base
commit**, at
`fixtures/self-bootstrap/readme-sync-candidate.json`:

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `hypothesis.id`, `hypothesis.statement` | what the candidate claims |
| `observable_delta.kind` | allowlisted delta kind the base evaluator knows |
| `observable_delta.expected_artifacts` | files the delta must produce or change |
| `observable_delta.required_assertions` | named assertions the base evaluator runs |
| `allowed_candidate_paths` | the only repository paths the candidate may change |
| `base_protected_paths` | paths whose tracked/untracked change is fatal |
| `writable_output_roots` | disposable roots the run may write |
| `forbidden_write_roots` | roots the run must never write |
| `external_report_schema` | shape of the machine-readable execution report |

Rules:

- v1 accepts only `observable_delta.kind` values the **base** evaluator
  implements. An unknown kind is `DESIGN_INCOMPLETE`; a manifest cannot declare
  new scoring logic.
- `allowed_candidate_paths` may not contain the evaluator, comparator,
  fixtures, result cases, contract or report paths. A manifest cannot widen its
  own permissions, because the manifest is read from the base snapshot, not
  from the candidate.
- The first real self-bootstrap uses **C2 as base and C3 as candidate**: C2
  contains the manifest and the base evaluator; C3 implements the README
  managed-block sync the manifest pre-declared.

## 3. CLI

```text
self-bootstrap-check.py
  --repo-root PATH
  --base-ref COMMIT
  --candidate-ref COMMIT
  --candidate-root PATH
  --candidate-manifest RELATIVE_PATH
  [--output PATH]
```

`--output` is an *external* machine-readable execution report — never the plan
file. It contains at least: schema version, base and candidate full SHAs, base
and candidate tree SHAs, requested vs observed HEAD, candidate worktree path
digest, base archive manifest SHA, candidate manifest SHA, protected-path diff,
each gate's state/reason/exit code, start and end phase, and the cleanup
result. It is written to an explicit non-symlink path with a temporary file plus
atomic replace, and the same JSON goes to stdout so CI can collect it.

## 4. Preconditions

1. `base_ref` and `candidate_ref` both resolve to commits and are **different**.
2. `base_ref` is an ancestor of `candidate_ref`.
3. `candidate_root` is an independent, **clean, detached** worktree at
   `candidate_ref`: `git status --porcelain=v1 --untracked-files=all`, the
   unstaged diff and the staged diff are all empty; the realpath of
   `git rev-parse --show-toplevel` equals the passed root; `HEAD` equals the
   candidate SHA.
4. `candidate_root`, repo root, base archive, fixture copy, output/report root
   and every manifest/result/evidence path pass lexical **and** realpath
   checks. v1 rejects symlinked worktree roots, symlinked inputs and symlinked
   protected directories, and refuses to leave a declared root.
5. The candidate manifest's relative path exists in the **base** snapshot and
   is read from there, never from the candidate.
6. Any tracked change to a protected evaluator/fixture/result-case path, any
   untracked protected file in the candidate, and any tracked or untracked
   repository change outside `allowed_candidate_paths` is `BLOCKED`.
7. Candidate `HEAD`, index/worktree status, base archive manifest and protected
   path hashes are recorded before the run and re-collected after. Any drift —
   except the pre-declared allowlist and the disposable output — is `BLOCKED`.

## 5. Base evaluator isolation

1. `git archive <base_ref>` unpacks the base evaluator, base comparator,
   fixtures, expected invariants, result cases and candidate manifest into a
   fresh `0700` temporary directory. The archive content is pinned by a
   canonical path list plus a SHA-256 manifest; symlink and hardlink escapes
   inside the archive are refused.
2. The base snapshot is made read-only after hashing and every hash is
   re-verified from Git objects afterwards. Any pre/post drift is `BLOCKED` and
   must never be "repaired" from candidate output.
3. The fixed comparator cases run **only the base snapshot's comparator**,
   never the candidate's. The base comparator's script hash must be identical
   before and after.
4. The candidate generator/validator receive only a disposable fixture copy,
   the candidate worktree and an independent writable output directory. Base
   expected results are never a writable candidate input. Every subprocess gets
   an explicit `cwd`, `HOME`, `TMPDIR` and output root pointing at disposable
   roots.
5. The base evaluator inspects candidate output itself — re-parsing README
   markers, manifests, results, evidence and the Git diff. A candidate
   validator reporting "pass" is not accepted as the only evidence.
6. Every temporary worktree and output root is cleaned up after the result is
   consumed. A cleanup failure is written to the report and makes the run
   `BLOCKED`; it is never silently ignored.

## 6. What the base evaluator checks

1. The `paper-agent` fixture generates both diagrams.
2. Both diagrams contain every required node, edge and boundary.
3. Missing-contract and missing-current-best cases yield `DESIGN_INCOMPLETE` or
   `FUNCTIONAL_BASELINE_MISSING`.
4. Identical inputs regenerate byte-identical output.
5. README markers match the `.mmd` bytes.
6. Nothing is written into a runtime directory; no secret is read or emitted.
7. The base comparator reproduces every fixed outcome:
   `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`, `CANDIDATE_REJECTED`,
   `ENVIRONMENT_BLOCKED`, `EVALUATION_BLOCKED`, `BASELINE_INVALIDATED`,
   `GENERALIZATION_REQUIRED`, `FUNCTIONAL_BASELINE_MISSING` and
   `DESIGN_INCOMPLETE` — and never reports a recommendation as a promotion.
8. Known-bad mutations are rejected or blocked: deleting a required state,
   relaxing the candidate comparator, editing an expected invariant, adding an
   untracked protected file.
9. The candidate is a distinct, clean, correctly-descended revision that
   satisfies the base-declared observable delta.

## 7. Accept / reject

```text
SKILL_BASELINE_COMMITTED_WITH_CANDIDATE_MANIFEST
  → DISTINCT_CLEAN_CANDIDATE_COMMIT
  → RUN_BASE_EVALUATOR_ON_CANDIDATE
  → STATIC_AND_DETERMINISM_CHECK
  → CHECK_PREDECLARED_OBSERVABLE_DELTA
       ├─ refs equal / not ancestor / dirty worktree → BLOCKED
       ├─ evaluator / fixture / result case changed  → BLOCKED
       ├─ required invariant lost                    → REJECTED
       ├─ no declared / observable delta             → REJECTED
       ├─ evaluator unavailable                      → BLOCKED
       └─ invariants preserved + delta observed       → HUMAN_REVIEW
                                                          ├─ reject → previous skill best
                                                          └─ accept → new skill best
```

The machine gate decides refs, protected inputs, structure, determinism,
boundaries, fixed outcomes and the pre-declared observable delta. A human keeps
the final veto on readability, simplicity, misleadingness and whether the change
actually helps a developer.

Passing this protocol says nothing about `hewo` product performance. It only
demonstrates that the protocol can tell a baseline from a candidate.
