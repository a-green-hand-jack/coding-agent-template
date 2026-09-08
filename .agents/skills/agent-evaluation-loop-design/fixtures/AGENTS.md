# Agent Evaluation Loop Design Fixtures

> **Role:** development-agent instructions for the agent-evaluation-loop-design skill's test fixtures. Not product behavior.

Fixed, provider-free fixtures used to verify the skill's own scripts.

`paper-agent/` is an abstract sample product Agent used to prove the diagram
generator scans a real runtime tree. It is not a product in this repository and
must not be installed or released.

`self-bootstrap/` holds the fixed comparator outcome cases and the pre-declared
self-bootstrap candidate manifest. These files are protected inputs: a
candidate under evaluation may not modify them.
