from .models import SourceCard
from .reliability import reliability_note
def build_source_cards() -> tuple[SourceCard, ...]:
    return (
        SourceCard("src-primary", "Public Research Bulletin", "primary", "https://example.com/research", "fresh", reliability_note("primary"), "A public bulletin reports a measured change.", "title, public URL, fixture timestamp", "safe_mock_fixture", ""),
        SourceCard("src-wire", "Independent News Wire", "wire", "https://example.org/news", "recent", reliability_note("wire"), "Independent reporting adds context and caveats.", "title, public URL, fixture timestamp", "safe_mock_fixture", ""),
    )
