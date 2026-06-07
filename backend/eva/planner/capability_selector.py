from __future__ import annotations


def _text(goal_text: str) -> str:
    return " ".join(str(goal_text or "").lower().split())


def infer_goal_intents(goal_text: str) -> list[str]:
    text = _text(goal_text)
    intents: list[str] = []
    if any(term in text for term in ("saved research", "research memory", "retrieve my notes", "what did i save", "my research")):
        intents.append("retrieve_memory")
    if any(term in text for term in ("review memory", "promote candidates", "recall stats")):
        intents.append("memory_review")
    if any(term in text for term in ("import note", "save research", "save note")):
        intents.append("research_memory_write")
    if "demo" in text or "public status" in text or "safety test" in text:
        intents.append("public_demo")
    if "dry run" in text or "dry-run" in text or "plan this" in text or text.startswith("plan "):
        intents.append("v2_planning")
    if "route this" in text or "route preview" in text:
        intents.append("route_preview")
    if any(term in text for term in ("open website", "open chatgpt", "open chrome", "search web", "browser", "website")):
        intents.append("browser_open")
    if any(term in text for term in ("read file", "edit file", "make report", "create document", "write file")):
        intents.append("file_or_document")
    if any(term in text for term in ("send whatsapp", "send email", "message ", "post ", "submit form")):
        intents.append("external_message")
    if any(term in text for term in ("delete", "shutdown", "install", "run powershell", "run shell", "terminal", "remove folder")):
        intents.append("destructive_or_system")
    if any(term in text for term in ("hackathon", "submission", "proposal", "report", "summary", "summarize")):
        intents.append("draft_content")
    if not intents:
        intents.append("unknown")
    return _dedupe(intents)


def select_capabilities_for_goal(goal_text: str) -> list[str]:
    intents = infer_goal_intents(goal_text)
    selected: list[str] = []
    if "retrieve_memory" in intents:
        selected.extend(["research_memory.retrieve", "research_memory.search"])
    if "memory_review" in intents:
        text = _text(goal_text)
        if "recall stats" in text:
            selected.append("research_memory.recall_stats")
        elif "promote" in text:
            selected.append("research_memory.promote_candidates")
        else:
            selected.append("research_memory.review_memory")
    if "research_memory_write" in intents:
        selected.append("research_memory.save")
    if "public_demo" in intents:
        text = _text(goal_text)
        if "status" in text:
            selected.append("public_release.status")
        elif "safety test" in text:
            selected.append("public_release.safety_test")
        else:
            selected.append("public_release.demo")
    if "v2_planning" in intents:
        selected.append("eva_v2.plan")
    if "route_preview" in intents:
        selected.append("eva_v2.route")
    if "draft_content" in intents:
        selected.append("eva_v2.plan")
    return _dedupe(selected)


def explain_capability_selection(goal_text: str, capability_ids: list[str]) -> str:
    if not capability_ids:
        return "No registered safe capability directly matched this goal; the planner will produce a preview-only unknown step."
    intents = ", ".join(infer_goal_intents(goal_text))
    capabilities = ", ".join(capability_ids)
    return f"Detected intents: {intents}. Selected capabilities: {capabilities}."


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out
