# Agent Development Evaluation Loop

> **Role of this document**
> - **Audience:** the development coding agent running one iteration of the product-Agent development loop.
> - **Authority:** normative. The ordered stages, their commands and their stop conditions bind each iteration.
> - **Tone:** imperative and procedural; numbered stages, each with the exact command that satisfies it.
> - **Language:** 中文（代码、命令、协议标识保留原文）.
> - **Contains:** the ordered loop stages from evaluation design through comparison, background execution of long runs, the evidence each stage must collect, and failure classification.
> - **Excludes:** product behavior of any kind (see `src/hewo/runtime/`), the evaluation contract's schema (see `.agents/skills/agent-evaluation-loop-design/references/evaluation-contract.md`), and downstream evidence and history (see `.agents/downstream-skeleton/workflows/`).

This workflow is for the **development coding agent**. It lives inside the
project but outside the product runtime. Do not copy it into
`src/hewo/runtime/`, and do not treat it as hewo behavior.

Repeat this loop for each product-agent iteration:

-1. **Cold start: confirm the problem with the human before designing anything.**
   Until the human has confirmed the problem definition and the product
   positioning, and a functionally complete baseline exists, the loop is not
   delegated to you. Show real provider-backed output rather than describing
   it, write your understanding back in plain language and ask for correction,
   and do not invent a metric to get past this step. If several candidates are
   rejected in a row, or no stable baseline appears, treat it as
   `UNDERSTANDING_MISMATCH` — a misread problem, not a weak candidate — and
   return here instead of tuning. `AGENTS.md` holds the normative rule; the
   states are `COLD_START_HUMAN_IN_LOOP` and `UNDERSTANDING_MISMATCH` in
   `agent-optimization-loop.mmd`.

0. **Design the evaluation before changing behavior.** Load
   `.agents/skills/agent-evaluation-loop-design/SKILL.md`. Write or update
   `.agents/development/<agent_name>/evaluation-contract.json` first, and regenerate
   the two diagrams so the product structure and the optimization state machine
   stay truthful:

   ```bash
   python3 .agents/skills/agent-evaluation-loop-design/scripts/generate-agent-diagrams.py \
     --agent <agent_name> --repo-root . --output-dir . --readme README.md
   python3 .agents/skills/agent-evaluation-loop-design/scripts/validate-agent-evaluation.py \
     --agent <agent_name> --repo-root . --output-dir . --readme README.md --strict
   ```

   Stop at step 1 while the state is `DESIGN_INCOMPLETE` or
   `FUNCTIONAL_BASELINE_MISSING`: those mean the product or the contract is
   unfinished, not that the Agent is slow or low-quality.

1. **Define or change behavior** in identity, skills, knowledge, workflows,
   memory policy, tools, and permissions. In this repository, product behavior
   belongs under `src/hewo/`; downstream repositories replace that with their
   own `src/<agent_name>/`.
2. **Validate structure** with `./.agents/scripts/validate-definition.sh <agent_name>`.
3. **Audit the repository scope**: run the template self-audit
   (`.agents/scripts/check-template-registry.py`, then
   `template-release-readiness` / `audit_template_release.py --agent hewo`) in
   this template repository, or run the consistency audit
   (`agent-consistency-audit` / `audit_agent.py --agent <agent_name> --strict`)
   inside a downstream repo with its own Agent name.
4. **Check clean infrastructure** with the repository's infrastructure-health
   script or equivalent clean-container gate.
5. **Run provider-backed behavior evidence** in Docker with credentials
   injected only at runtime through a backend-specific explicit flag or
   read-only auth/key mount. A build, CLI startup, or unauthenticated run is
   infrastructure-only evidence, not product-agent behavior evidence.
6. **Prefer background execution for long validation.** Product-agent tasks can
   be long. Submit long E2E or internal case runs through the loop runner's
   registered background mode so the human and development coding agent can
   keep interacting:

   ```bash
   ./.agents/scripts/run-agent-loop.sh --background --provider <provider> --model <model> \
     --pi-auth-file "$HOME/.pi/agent/auth.json" "<task>"
   ./.agents/scripts/run-agent-loop.sh --run-status <run_id>
   ./.agents/scripts/run-agent-loop.sh --clean-run <run_id>
   ./.agents/scripts/run-agent-loop.sh --gc --older-than 7
   ```

   The whole preflight runs in the foreground, so an invalid invocation is
   rejected there instead of becoming a background run to chase. The registry
   records secret-free metadata only and must be cleaned up once the result is
   consumed.

   Submitting freezes the worktree into a snapshot owned by that run. Every
   stage — validation, audit, image build, case, and the verifier that
   decides pass/fail — reads the snapshot, so the product Agent may be edited
   the moment the submit returns without changing what an in-flight run tests
   or what its evidence claims. `--run-status` reports each run's
   `definition_revision` and `image`, which is how you tell which version a
   run is testing.
7. **Collect evidence**: artifact path, trajectory path, scrubbed trajectory
   path, backend/provider/model, definition revision, and credential-source
   flag. Save only scrubbed artifacts or durable lessons; never save raw
   provider sessions or secrets.
8. **Classify failures and iterate**: decide whether the problem is in the
   product definition, template infrastructure, provider wiring,
   case/verifier, or external provider availability. Fix the appropriate
   layer, then rerun the relevant loop stages.
9. **Compare, do not assert.** When a change claims an improvement, produce a
   candidate result under the same canonical condition manifest as the current
   best and run the thin comparator:

   ```bash
   python3 .agents/skills/agent-evaluation-loop-design/scripts/compare-evaluations.py \
     --contract .agents/development/<agent_name>/evaluation-contract.json \
     --current-best <path>/current-best-result.json \
     --candidate <path>/candidate-result.json
   ```

   It never runs a provider and never updates the current best. Promotion to
   `ACCEPTED_AS_CURRENT_BEST` is a separate human/approved-runner gate, and a
   product-general claim additionally needs an independent holdout or canary
   plus domain review.

`.agents/scripts/run-agent-loop.sh` is the executable wrapper for this loop when it is
available. It should orchestrate existing scripts rather than duplicate their
internals; `.agents/scripts/run-case.sh` remains the single implementation of the
provider-backed internal case / verifier / trace-scrub stage. Legacy `benchmark`
stage/output names are compatibility aliases only (see `.agents/development/hewo/cases/README.md`).
真正 benchmark 由外部评测方对已发布 Agent 独立开展，不能用内部 smoke 代替。

This template workflow is not downstream memory. A downstream repository may
adapt the method, but must replace template Agent names, issue history,
benchmarks, provider assumptions, evidence destinations, and background-state
paths with its own.
