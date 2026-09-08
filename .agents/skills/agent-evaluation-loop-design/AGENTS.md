# Agent Evaluation Loop Design Skill

Development-only instructions for the skill that teaches the development coding
agent how to design a product-Agent optimization loop.

This directory is development infrastructure. Never copy it into
`src/<agent_name>/runtime/`, a release archive, or a final Docker image, and
never treat its fixtures as product behavior or as acceptance evidence.

The scripts here are deterministic, dependency-free, read-only with respect to
product runtimes, and must never call a provider or read credentials.
