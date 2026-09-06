# HeWo Runtime Knowledge

HeWo is an infrastructure probe, not a benchmark-specific solver. A valid
smoke run demonstrates that the installed product can load its runtime
definition, use a project workspace, load a product skill, write an artifact,
and report a checked result. The runtime owns a minimal uv-managed tool
environment so a skill can verify a real tool invocation. Development-agent
instructions and provider credentials are never product inputs.

Infrastructure smoke sentinel: `HEWO_KNOWLEDGE_OK`.
