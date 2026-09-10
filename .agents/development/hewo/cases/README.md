# HeWo 内部 Case 验收

> **Role of this document**
> - **Audience:** 运行 HeWo 内部 smoke case 并报告证据的 development coding agent。
> - **Authority:** normative；内部验收不得声明 benchmark 或性能改进。
> - **Tone:** imperative；固定输入、保留证据、限定声明。
> - **Language:** 中文（代码、命令、协议标识保留原文）。
> - **Contains:** 内部 case 位置、执行链、证据边界与兼容接口。
> - **Excludes:** 产品行为（`src/hewo/runtime/`）、外部 benchmark 协议（`.agents/skills/agent-evaluation-loop-design/references/evaluation-contract.md`）。

本目录仅包含 HeWo 内部基础设施 smoke task、manifest 和 deterministic verifier，不是真正的 benchmark。通过只说明该次 smoke 验收成立，不能证明性能或泛化改善。契约保持 `.agents/development/hewo/evaluation-contract.json` 的 `infrastructure-smoke-only`。

```text
.agents/scripts/run-case.sh -> docker/run-hewo-e2e.sh -> installed product
                          -> real task -> artifact + trajectory -> verifier
```

固定 task/verifier、definition revision、不可变 image ID、backend/provider/model 与 credential-source flag；分享前 scrub 轨迹。不得预写产品 artifact 或针对 grader 修改 runtime。provider/凭据/基础设施失败属于 `ENVIRONMENT_BLOCKED`，case/verifier/证据失败属于 `EVALUATION_BLOCKED`，都不是性能回归。

## 兼容边界

- 新入口为 `.agents/scripts/run-case.sh`；旧脚本路径移除，不新增公共 wrapper。
- 使用 `CASE_RUN_DIR`、`CASE_WORKSPACE`、`CASE_API_KEY_ENV`；对应 `BENCHMARK_*` 仅为兼容回退，新变量非空时优先。`PI_AUTH_FILE`、`PI_MODELS_FILE` 和 `E2E_WORKSPACE` 保持原意。
- JSON 新字段为 `case`，旧 `benchmark` 是同值兼容别名；loop 同时提供 `case_ran` 和旧 `benchmark_ran`，标记 `evidence_scope=infrastructure-smoke-only`。
- loop 保留旧 stage 名 `benchmark`、`benchmark.log` 和 stage result 协议，避免破坏已存 run/消费者；`compatibility_aliases` 明确其内部 case 含义，不重复执行阶段。

## 外部独立性能评测

真正 benchmark 由外部评测方对已发布 Agent 独立开展。使用固定条件、独立指标/verifier、重复测量和外部证据；内部 case 不能代替它。通用 performance contract schema、comparison 状态、外部 benchmark fixtures 保持独立协议，不随本目录改名。参见 `.agents/skills/agent-evaluation-loop-design/`。
