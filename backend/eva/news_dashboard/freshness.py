def freshness_label(age_hours: int) -> str:
    return "fresh" if age_hours <= 24 else "recent" if age_hours <= 72 else "stale"
def freshness_policy_text() -> str:
    return "Freshness policy\nfresh <=24h; recent <=72h; stale >72h. Labels are deterministic metadata."
