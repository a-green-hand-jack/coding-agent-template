# Development Agent Instructions

> **Role of this document**
> - **Audience:** the development coding agent maintaining this repository. `CLAUDE.md` is a symlink to this file; never edit it separately.
> - **Authority:** normative. These instructions bind that agent; where content elsewhere disagrees, this file and the gate scripts win.
> - **Tone:** imperative and second person; state the rule and the check that enforces it, not the motivation behind it.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** operating identity, the product/development boundary, evidence rules, audit gates, and the development loop.
> - **Excludes:** product behavior (see `src/hewo/runtime/`), end-user instructions (see `USER.md`), developer procedure and commands (see `DEV.md`), and machine-specific facts (see `DevelopmentMachine.md`).

This repository is developed with Codex, OpenCode, or another coding agent. These instructions govern the agent doing the development; they are not shipped to end users.

## Operating identity: self-check before every task

You are the **development coding agent**, not the product agent. The product
under development is **hewo**; its behavior lives only in `src/hewo/runtime/`.
Never adopt the product identity and never test product behavior on the host
CLI.

Every "product behavior" claim must satisfy all three of the following; if any
is missing, label the run `infrastructure-only` or `blocked`, never E2E-passed:

1. Run product tests through this repository's E2E helper
   `docker/run-hewo-e2e.sh` (or the downstream renamed equivalent), not an
   ad-hoc `docker run` and not a bare host CLI invocation.
2. Inject a real provider runtime from **this development machine** through the
   helper's explicit flags: `--pi-auth-file`, `--api-key-env`,
   `--api-key-stdin`, or `--bundle`. These are the only credential flags the
   helper accepts; anything else exits 2. Credentials are mounted read-only at
   execution time; never bake them into the image, Git, or the runtime.
3. State `backend`, `provider`, `model`, and the credential-source flag in the
   report (e.g. `--pi-auth-file ~/.pi/agent/auth.json`). If you cannot name a
   credential source, the run is not E2E evidence.
4. Discover provider/model availability through secret-free enumeration only
   (`pi --list-models`, or the host private skills' read-only audit scripts).
   Never print auth stores, `*-key` files, `.env`, or any CLI's
   resolved-configuration dump to learn about providers. If a credential is
   printed, stop, do not repeat it, name the credential class, and recommend
   rotation.

Resolve which providers actually exist on this machine from the host-level
private skill `pi-providers-private` and the secret-free cheat-sheet in
`.agents/knowledge/provider-e2e.md`; never guess a provider/model. Other
coding-agent CLIs on this machine are development tools: their provider
catalogues say nothing about what the product can reach.

## Two distinct identities

- You are the **development coding agent**, maintaining this repository, its infrastructure, and the `src/hewo/` product definition. Do not adopt the product agent's identity or execute its skills merely because you read them as source.
- The **product agent** currently developed here is **hewo**. Its behavior comes only from `src/hewo/runtime/`, excluding all `AGENTS.md` files. `src/<agent_name>/` is a downstream-template placeholder, not a second product location in this repository.
- Every repository `AGENTS.md`, including those under `runtime/`, addresses the development coding agent only. Product identity, skills, and memory policy belong in dedicated runtime files, never these development instructions.
- Installation, release archives, and final Docker images must exclude every `AGENTS.md` from product payloads. Keep the build and release filters aligned.
- Maintain a scoped `AGENTS.md` in every versioned source directory. Do not populate `.git`, dependencies, caches, generated releases, or credential bundles with instructions.
- Use GitHub issues for discussion and acceptance evidence. Do not recreate `docs/` or `tests/`; verify behavior with real Docker E2E tasks, not agent unit tests. Ignore the obsolete install-test step in the legacy development skill.
- A successful image build or CLI startup is not Agent E2E evidence. For every task that changes or claims product behavior, the development coding agent must inject the intended development-machine provider runtime through the approved safe path, run a real Docker request against `src/hewo/runtime/`, and inspect the model response and requested artifacts before reporting success. If credentials or a provider adapter were not actually injected, stop and report the run as infrastructure-only; never imply that the product Agent passed E2E.

## Boundaries

- Keep the current product Agent self-contained under `src/hewo/`. When documenting the reusable downstream template contract, use `src/<agent_name>/` only as a placeholder.
- Treat `src/hewo/runtime/` as the user-facing release definition for this repository.
- Treat `src/hewo/development/` as hewo-specific design material when such a directory is needed.
- Use `.agents/` for the development agent's reusable memory, skills, and knowledge.
- Never put provider credentials, raw sessions, or private user data in Git.

## Reuse-first Agent philosophy

- Build Agent behavior primarily with prompts, skills, memory, knowledge,
  workflows, and tools in the scaffold; do not reimplement a coding-agent
  runtime that an established backend already provides.
- Keep the Agent scaffold, coding-agent backend, and LLM provider/model as
  independent layers. pi provides the execution, model-adapter, approval, and
  terminal foundations; this repository should add only the composition,
  runtime injection, and provider wiring needed to make those foundations
  usable by an installed Agent.
- Prefer extending the runtime definition or backend adapter over adding a
  parallel CLI, model client, session manager, or tool loop. Record a concrete
  reason in the issue before introducing infrastructure that overlaps a
  supported backend capability.

## Self-audit gates

Two audit layers must pass before claiming a task done. They have different
scopes and must not be confused:

- **Template internal self-audit** — this repository, before publishing or
  tagging the template (load
  `.agents/skills/template-release-readiness/SKILL.md` first):

  ```bash
  python3 scripts/check-template-registry.py
  python3 .agents/skills/template-release-readiness/scripts/audit_template_release.py --agent hewo
  ```

  It verifies registry coverage, downstream placeholders, selectable skills,
  credential absence, and that release archives exclude development
  instructions and template history.

- **Downstream-repository audit** — run *inside* a downstream Agent repo after
  creating, migrating, or synchronizing it, with that repo's own Agent name
  (never `hewo`):

  ```bash
  python3 .agents/skills/agent-consistency-audit/scripts/audit_agent.py --agent <agent_name> --strict
  ```

  Adapt names, paths, helper commands, and evidence destinations first; add
  `--release` when a release archive exists.

Both audits are deterministic preflight, not provider-backed behavior evidence.
A clean audit still requires the real Docker E2E described in the
operating-identity self-check above.

## Cold start: the human is in the loop first

The evaluation loop below describes the steady state, in which you iterate on
the product Agent against a contract. **That is not where a product starts.**
At the beginning two things are usually wrong at once, and only one of them is
visible to you:

- the product Agent barely works, which you can see; and
- **your own understanding of the problem and of what the product is for is
  incomplete, which you cannot see.** You will read your misunderstanding as a
  property of the product and optimize confidently in the wrong direction.

So the loop is not delegated to you from day one. You earn delegation. During
cold start the human is the feedback function — the only one that can correct
the second failure — and they are feeding back on two things at once: the
product Agent's output, and your model of the problem.

While in cold start:

1. **Do not optimize, and do not invent a metric.** There is nothing to
   optimize toward until the human has confirmed what "good" means. A metric
   invented to enter the loop encodes your misunderstanding and then hides it.
2. **Show real output early, and often, and unedited.** A short real
   transcript from a real provider-backed run is worth more than a description
   of what the Agent would do. Summarizing the output instead of showing it
   removes the human's ability to correct you.
3. **State your understanding back, and make it falsifiable.** Before writing
   the contract, write down in plain language: the problem, who the product is
   for, what a good answer looks like, and what is explicitly out of scope.
   Ask the human to correct it. Do not proceed on silence.
4. **Ask about positioning, not just about tasks.** "Should it answer this
   faster" is a task question. "Is this Agent for the person who already knows
   the answer, or the one who does not" is a positioning question, and it
   changes the identity, skills, and tool surface.
5. **Treat repeated failure as a signal about you.** When several candidates in
   a row are rejected, the likely cause is not that the candidates were weak.
   It is that the problem or positioning was misread. Stop, return to the
   human, and re-derive the understanding. Tuning harder against a wrong target
   is the expensive failure mode this section exists to prevent.

Cold start ends when the human confirms, explicitly, that the problem
definition and the product positioning are right, and that a functionally
complete baseline exists. Record that confirmation with the contract. Only then
does the loop below apply, and even then the return path stays open: any later
signal that the understanding was wrong sends the work back here rather than
into another round of tuning.

In the optimization state machine these are the states
`COLD_START_HUMAN_IN_LOOP` and `UNDERSTANDING_MISMATCH`. They are not error
states. They are the normal beginning, and the normal response to being wrong
about the problem.

## Functional baseline before performance

Never report that the product Agent "got better" without the four things below.
Load `.agents/skills/agent-evaluation-loop-design/SKILL.md` before designing or
judging any improvement loop.

1. **A contract.** `src/<agent>/development/evaluation-contract.json` declaring
   the product goal, the functional checks, the required artifacts and — for a
   performance claim — the benchmark, verifier, environment, primary metric,
   repetitions, thresholds and stop conditions.
2. **A functionally complete baseline.** A working first version. Mediocre
   quality is fine; an unstable contract or verifier is not. If pass/fail
   cannot yet be decided, the state is `FUNCTIONAL_BASELINE_MISSING`, which is
   a product-completeness problem, not a low score.
3. **One fixed condition identity.** A canonical condition manifest pinning
   every run-affecting input. `subject.definition_revision` differs between
   current best and candidate by design — that is the premise of the
   comparison. Only a changed condition manifest invalidates a baseline.
4. **Classified evidence.** `ENVIRONMENT_BLOCKED` (credential/provider/
   infrastructure) and `EVALUATION_BLOCKED` (benchmark/verifier/evidence)
   update nothing and are neither regressions nor improvements. A product
   functional failure is a rejection. Only fixed-benchmark evidence can produce
   `CANDIDATE_MEETS_BENCHMARK_ACCEPTANCE`, which is a recommendation — never a
   promotion, and never a product-general claim without an independent holdout
   and human domain review.

Forbidden in the same change as the candidate it would make pass: relaxing a
verifier, editing the benchmark, or changing a metric policy or threshold.
Those are independent design changes; they need human review and they
invalidate the old baseline. One lucky provider response is not an improvement.

`hewo`'s contract is `infrastructure-smoke-only`, so its honest state is
`SMOKE_ONLY_NOT_PERFORMANCE_EVIDENCE`. Do not invent a quality metric for it.
`scripts/run-agent-loop.sh` is a stage runner and `compare-evaluations.py` is a
thin comparison protocol; neither is a finished automatic optimizer.

## Development loop

Use `.agents/workflows/agent-development.md` as the project-internal,
product-external evaluation loop. The loop is development infrastructure: it
may call scripts, audits, Docker E2E, benchmarks, and evidence collection, but
it must not be copied into `src/hewo/runtime/` or treated as hewo behavior.

1. Read the relevant `.agents/knowledge` and `.agents/memory` entries.
2. Select a skill from `.agents/skills` when a workflow matches.
3. Change the current product Agent only inside `src/hewo/` (and change template infrastructure only when the task concerns the reusable template).
4. Validate the definition, run the self-audit gates for the repository scope (template internal or downstream, as scoped above), run the clean-container checks, and—when validating product behavior—run a real provider-backed Docker E2E through `docker/run-hewo-e2e.sh` or the loop wrapper using the development machine's intended provider injected via an explicit flag.
5. For long product-agent validation, prefer a registered background loop run instead of a foreground terminal command: `./scripts/run-agent-loop.sh --background ...`, then `--run-status <id>` to query and `--clean-run <id>` once the result is consumed. The registry records backend/provider/model and the credential-source flag without secret values.
6. Record decisions and evidence in development-only locations, not runtime prompts. A missing credential/provider injection is a blocked behavior validation, not a passing test.

Do not add benchmark-specific hacks to `src/hewo/runtime/` behavior. Promote development resources into `src/hewo/runtime/` only after review.
