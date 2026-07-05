from __future__ import annotations

from .project_inventory import ProjectInventory, build_project_inventory


def draft_readme_section(topic: str, project_context: object | None = None) -> str:
    title = _title(topic or "Project Notes")
    return "\n".join(
        [
            f"## {title}",
            "",
            "Draft purpose: describe the feature, workflow, or decision in plain language.",
            "",
            "- What it does:",
            "- Why it matters:",
            "- How to verify it:",
            "- Safety or limitations:",
            "",
            "Preview only. No file was created or modified.",
        ]
    )


def draft_project_summary(project_inventory: ProjectInventory | None = None) -> str:
    inventory = project_inventory or _safe_inventory()
    project_types = ", ".join(inventory.project_types[:5]) if inventory.project_types else "unknown project type"
    key_file_items = _flatten_key_files(inventory)[:6]
    key_files = ", ".join(key_file_items) if key_file_items else "no key files detected"
    return "\n".join(
        [
            "# Project Summary Draft",
            "",
            f"This project appears to be: {project_types}.",
            f"Key files observed: {key_files}.",
            "",
            "Suggested summary:",
            "This repository contains an Eva assistant system with local-first safety, planning, agent, and verification surfaces. The summary should be edited by a human before publication.",
            "",
            "Preview only. No file was created or modified.",
        ]
    )


def draft_missing_files_recommendations(project_inventory: ProjectInventory | None = None) -> str:
    inventory = project_inventory or _safe_inventory()
    missing = inventory.missing_recommended_files[:8] if inventory.missing_recommended_files else ["No common missing-file recommendation was detected."]
    lines = ["# Missing Files Recommendations Draft", ""]
    lines.extend(f"- {item}" for item in missing)
    lines.extend(["", "Preview only. No file was created or modified."])
    return "\n".join(lines)


def draft_report_outline(title: str, context: object | None = None) -> str:
    heading = _title(title or "Report")
    return "\n".join(
        [
            f"# {heading}",
            "",
            "## 1. Executive Summary",
            "Briefly state the purpose, outcome, and current limitations.",
            "",
            "## 2. Current State",
            "Summarize the observed files, systems, and verification status.",
            "",
            "## 3. Findings",
            "List important observations with evidence.",
            "",
            "## 4. Risks And Constraints",
            "Call out safety, privacy, and execution limits.",
            "",
            "## 5. Recommended Next Steps",
            "Prioritize the smallest safe follow-up actions.",
            "",
            "Preview only. No file was created or modified.",
        ]
    )


def draft_changelog_entry(summary: str) -> str:
    item = str(summary or "Describe the change").strip()
    return "\n".join(
        [
            "## Draft Changelog Entry",
            "",
            "### Changed",
            f"- {item}",
            "",
            "### Verification",
            "- Add the relevant verifier commands and outcomes here.",
            "",
            "Preview only. No file was created or modified.",
        ]
    )


def draft_todo_list_from_project_inventory(project_inventory: ProjectInventory | None = None) -> str:
    inventory = project_inventory or _safe_inventory()
    missing = inventory.missing_recommended_files[:5]
    lines = ["# Project TODO Draft", "", "- Review generated drafts before applying any future write."]
    if missing:
        lines.extend(f"- Consider adding or updating {item}." for item in missing)
    else:
        lines.append("- Keep docs and verifier scripts synchronized with the current behavior.")
    lines.extend(["- Run focused verifiers before any checkpoint commit.", "", "Preview only. No file was created or modified."])
    return "\n".join(lines)


def _safe_inventory() -> ProjectInventory:
    return build_project_inventory(".")


def _flatten_key_files(inventory: ProjectInventory) -> list[str]:
    output: list[str] = []
    for items in getattr(inventory, "key_files", {}).values():
        output.extend(str(item) for item in items)
    return output


def _title(value: str) -> str:
    words = " ".join(str(value or "").strip().split())
    return words[:80] if words else "Draft"
