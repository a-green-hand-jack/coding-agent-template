# Release Checklist

- [ ] `src/<agent_name>/runtime/` is the single behavior source.
- [ ] Development resources remain under `src/<agent_name>/development/` or `.agents/`.
- [ ] Dependencies and runtime versions are pinned in the release manifest.
- [ ] A fresh Docker container installs through the public `install.sh` path.
- [ ] No source checkout, host OpenCode configuration, or preinstalled Skills is used.
- [ ] Provider credentials are injected only at runtime and absent from image layers and traces.
- [ ] A representative real task completes with final artifact and scrubbed trajectory.
- [ ] A stable benchmark runs with model, runtime, definition, and dataset recorded.
- [ ] Failures produce general behavior fixes, not benchmark-specific hacks.
