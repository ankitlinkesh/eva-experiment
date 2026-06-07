# Eva Planner v3

Planner v3 is Eva's structured task decomposition foundation. In Phases 10A and 10B it is planning-only: it can turn a user goal into safe, capability-aware steps, validate the plan, and explain missing information, but it does not execute those steps.

## What It Uses

Planner v3 reads existing metadata surfaces:

- capability registry
- capability permission matrix
- capability-to-resource mapping
- tool schema previews
- explicit v2 dry-run concepts
- public/private safety status

It does not create a duplicate registry.

## Task Step Model

Each planned step includes:

- step title and description
- step type
- capability id when known
- resource id when known
- provider or agent
- input summary and expected output
- risk level
- permission status
- availability status
- dependencies
- notes

The plan summary also records required capabilities, blocked capabilities, confirmation or override needs, and the next recommended action.

## Phase 10B Plan Quality

Phase 10B adds a deterministic quality layer over the existing Phase 10A planner:

- reusable plan templates
- validation checks
- plan quality scoring
- deterministic critique and improvement suggestions
- missing-information detection
- safer next-action recommendations

This layer is still metadata and planning only. It does not call a cloud model, run tools, control apps, read private data, or execute planned steps.

## Templates

Current templates:

- `saved_research_summary`: retrieve local Research Memory notes, summarize them, state limitations, and suggest search/export if needed.
- `public_demo_safety`: classify a risky/demo request, explain blocked or confirmation-gated results, and suggest a demo-safe path.
- `coding_project_review`: identify project context, plan read-only inspection, identify tests/verifiers, define patch boundaries, and ask before edits or execution.
- `report_generation`: gather report requirements, retrieve memory/research, draft outline/content, and ask before saving/exporting.
- `browser_research`: clarify public research scope, plan public-source search, compare sources, and keep browser execution disabled.
- `external_message`: draft message content, require explicit confirmation, and keep send unavailable in this phase.
- `destructive_or_system_action`: detect destructive/system risk, require future override/checkpoint, and suggest safe dry-run alternatives.

Templates guide the plan structure. They do not bypass capability resolution, permission metadata, or the preview-only safety boundary.

## Validation And Review

Plan validation checks that:

- plans have clear steps
- risky steps include permission status
- external message steps include confirmation checkpoints
- destructive/system steps are blocked or override-required
- unknown capabilities are not treated as safely executable
- preview-only plans are not marked executable
- multi-step output plans include verification/checklist steps when useful
- user-facing planner fields do not contain secret-looking data or absolute Windows paths

Plan review adds:

- missing information prompts
- deterministic critique
- improvement suggestions
- a quality score from `0.0` to `1.0`

Example missing-information prompts:

- hackathon submission: project folder/name, submission format, deadline
- report generation: topic, output format, source requirements
- WhatsApp/email message: exact recipient and exact message
- motor comparison: models/specs and criteria such as thrust, efficiency, battery voltage, prop size, weight, or KV

## Safety Behavior

Planner v3 does not execute browser actions, file writes, shell commands, MCP tools, Playwright, PyAutoGUI, screen watching, WhatsApp sending, email sending, form submission, vector search, or normal-chat v2 routing.

Risk handling:

- external messages, posts, and submits are confirmation-gated
- delete, overwrite, install, shutdown, shell, and system-changing actions are blocked or override-gated
- unknown capabilities become preview-only or blocked steps
- private data reads remain unavailable unless a future explicit safe delegate exists

## Commands

- `eva planner status`
- `eva plan <goal>`
- `eva planner plan <goal>`
- `eva planner explain <goal>`
- `eva plan templates`
- `eva planner templates`
- `eva plan validate <goal>`
- `eva planner validate <goal>`
- `eva plan review <goal>`
- `eva planner review <goal>`

Examples:

- `eva plan use my saved research about Eva and summarize it`
- `eva plan send WhatsApp to mom saying hi`
- `eva plan delete Downloads folder`
- `eva planner explain prepare my hackathon submission`
- `eva plan validate use my saved research about Eva`
- `eva plan review compare drone motors and make a report`

## Output

Planner output is human-readable and avoids raw dictionaries, dataclass representations, stack traces, secret paths, raw secrets, absolute Windows paths, and internal runtime paths.

Normal plan output can include:

- template used
- plan quality
- missing information
- validation warnings
- critique/improvement suggestions
- next safest action

## Current Limitations

- No execution in Phases 10A or 10B.
- No MCP, Playwright, PyAutoGUI, shell, browser control, screen watching, or WhatsApp sending is enabled.
- Normal chat is not routed through Planner v3.
- Research Memory context is only planned when explicitly requested.
- Eva remains a local data/control assistant that can use API-backed LLM reasoning elsewhere when configured, but this planner phase makes no cloud calls.
- Template matching and quality scoring are deterministic heuristics, not a full reasoning engine.

## Future Path

Later Planner v3 phases can connect these structured plans to explicit permission sessions, safe executors, verifiers, and rollback checks. Phase 10B only improves the plan structure, validation, and review quality.
