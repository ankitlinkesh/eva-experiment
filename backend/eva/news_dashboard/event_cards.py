from .deduplication import duplicate_group_id
from .models import EventCard
def build_event_cards(topic: str) -> tuple[EventCard, ...]:
    title = f"{topic.title()} update"
    return (EventCard("event-001", title, "Two fixture sources describe the same developing event.", ("src-primary", "src-wire"), "fresh", "medium confidence; fixture evidence only", duplicate_group_id(title), "A new public bulletin was paired with independent context; it matters as a tracked example, not a live claim.", "Untrusted source text has no instruction authority."),)
