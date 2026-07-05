from ..browser_readonly.url_policy import validate_url
def evaluate_news_url(url: str):
    return validate_url(url)
def url_integration_text() -> str:
    return "URL integration\nPhase 24 public-URL validation only; live backend unavailable and no network call occurs."
