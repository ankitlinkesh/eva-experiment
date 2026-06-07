# Eva Agent Framework v1

Agent Framework v1 gives Eva's specialist subsystems a shared lifecycle interface so Planner v3 steps can be assigned consistently in future executor phases.

This phase is framework, status, explain, and dry-run only. It does not execute planned tasks.

## Lifecycle

Each registered agent exposes:

- `plan`
- `dry_run`
- `execute`
- `observe`
- `verify`
- `rollback`
- `explain`

In Phase 11A:

- `plan` and `dry_run` are available as previews.
- `explain` and status commands are available.
- `execute` refuses by default with an Agent Framework v1 disabled-execution message.
- `observe`, `verify`, and `rollback` return preview/unavailable results unless a later phase explicitly enables a safe path.

## Registered Agents

Initial registered agents:

- `ResearchAgent`: Research Memory, saved research, local research metadata, and safe public-research planning.
- `MemoryAgent`: local memory and task-context planning.
- `SafetyAgent`: permission, privacy, destructive action, and cloud-context precheck planning.
- `BrowserAgent`: browser and Chrome task planning only.
- `DesktopAgent`: desktop and visible UI task planning only.
- `MediaAgent`: Spotify/YouTube media task planning only.
- `CodeAgent`: Code Intelligence and workspace review planning only.
- `PlannerAgent`: Planner v3 templates, validation, and review.
- `PublicReleaseAgent`: public release, demo, safety simulator, and hardening status.
- `SupervisorAgent`: legacy specialist routing preview.

## Planner-To-Agent Delegation

The command `eva agents dry run plan <goal>`:

1. Builds a Planner v3 preview plan.
2. Selects an agent for each step using step metadata, capability id, and resource mapping.
3. Calls each agent's `dry_run`.
4. Formats the assignments and what each agent would do.

No tools are executed, no browser or desktop is controlled, and no message or file action runs.

## Commands

- `eva agents`
- `eva agents status`
- `eva agent list`
- `eva agent <agent_name>`
- `eva agent capabilities <agent_name>`
- `eva agents matrix`
- `eva agents dry run plan <goal>`
- `eva agent explain <agent_name>`
- `eva agent framework status`

Examples:

- `eva agents status`
- `eva agent ResearchAgent`
- `eva agent explain BrowserAgent`
- `eva agents dry run plan use my saved research about Eva`
- `eva agents dry run plan send WhatsApp to mom saying hi`

## Safety Limits

Phase 11A does not enable:

- MCP execution
- Playwright execution
- PyAutoGUI execution
- browser control
- desktop control
- screen watching
- WhatsApp sending
- email sending
- file writes
- shell execution
- package installs
- cloud embeddings
- vector search by default
- normal chat routing through the new agent framework

Eva remains a local data/control assistant that can use API-backed LLM reasoning elsewhere when configured. This framework phase makes no cloud calls and does not read secret files.

## Future Path

Later phases can connect the shared lifecycle to permission sessions, safe read-only delegates, verified executors, observation, verification, and rollback. Those phases must keep explicit confirmation, override, and refusal boundaries in place.

