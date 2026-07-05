def normalize_topic(topic: str) -> str:
    return " ".join(str(topic or "world events").strip().split())[:120]
def topic_model_text() -> str:
    return "Topic model\nLocal deterministic topic labels only; no search or crawler starts."
