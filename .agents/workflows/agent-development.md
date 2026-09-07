# Agent Development Evaluation Loop

This workflow is for the **development coding agent**. It lives inside the
project but outside the product runtime. Do not copy it into
`src/hewo/runtime/`, and do not treat it as hewo behavior.

Repeat this loop for each product-agent iteration:

1. **Define or change behavior** in identity, skills, knowledge, workflows,
   memory policy, tools, and permissions. In this repository, product behavior
   belongs under `src/hewo/`; downstream repositories replace that with their
   own `src/<agent_name>/`.
2. **Validate structure** with `./scripts/validate-definition.sh <agent_name>`.
3. **Audit the repository scope**: run the template self-audit
   (`scripts/check-template-registry.py`, then
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
   be long. Use the loop runner's registered background mode for long E2E or
   benchmark runs so the human and development coding agent can keep
   interacting. Every background run must be queryable, record only
   secret-free metadata, and be cleaned up after its result is consumed.
7. **Collect evidence**: artifact path, trajectory path, scrubbed trajectory
   path, backend/provider/model, definition revision, and credential-source
   flag. Save only scrubbed artifacts or durable lessons; never save raw
   provider sessions or secrets.
8. **Classify failures and iterate**: decide whether the problem is in the
   product definition, template infrastructure, provider wiring,
   benchmark/verifier, or external provider availability. Fix the appropriate
   layer, then rerun the relevant loop stages.

`scripts/run-agent-loop.sh` is the executable wrapper for this loop when it is
available. It should orchestrate existing scripts rather than duplicate their
internals; `scripts/run-benchmark.sh` remains the single implementation of the
provider-backed benchmark / verifier / trace-scrub stage.

This template workflow is not downstream memory. A downstream repository may
adapt the method, but must replace template Agent names, issue history,
benchmarks, provider assumptions, evidence destinations, and background-state
paths with its own.
