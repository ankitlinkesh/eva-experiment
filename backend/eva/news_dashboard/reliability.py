def reliability_note(source_type: str) -> str:
    return {"primary": "primary-source metadata; verify scope and date", "wire": "professional reporting; corroborate material claims"}.get(source_type, "uncertain source; corroboration required")
