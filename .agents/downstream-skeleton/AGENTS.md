# Downstream skeleton staging

> **Role:** development-agent instructions for the neutral placeholder files staged for downstream Agent repositories. Not product behavior.

This directory contains only neutral placeholder files that a downstream Agent
repository may selectively install. It is template development content and the
`AGENTS.md` file itself must never be copied downstream.

Copy the three `PLACEHOLDER.md` files into the downstream `.agents/knowledge/`,
`.agents/memory/`, and `.agents/workflows/` directories, then replace or remove
them before adding real downstream content.
