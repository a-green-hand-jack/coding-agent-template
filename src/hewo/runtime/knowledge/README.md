# HeWo Runtime Knowledge

HeWo is a complete Hello World reference Agent, intentionally scoped to its
purpose rather than deliberately degraded or incomplete. It also exercises the template infrastructure: a valid smoke run
demonstrates that the installed product can load its runtime definition, use a
project workspace, load a product skill, write an artifact, and report a
checked result. The runtime owns a minimal uv-managed tool environment so a
skill can verify a real tool invocation. The execution backend, LLM provider,
model, development-agent instructions, and provider credentials are supplied
outside the product runtime and are never product inputs.

Infrastructure smoke sentinel: `HEWO_KNOWLEDGE_OK`.
