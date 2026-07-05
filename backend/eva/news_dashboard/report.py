from .mock_feeds import build_mock_dashboard
def news_dashboard_report(topic: str = "world events") -> str:
    d = build_mock_dashboard(topic)
    return f"News / Web Intelligence Dashboard\nTopic: {d.topic}\nSources: {len(d.source_cards)}\nEvents: {len(d.event_cards)}\nStatus: {d.final_status}"
