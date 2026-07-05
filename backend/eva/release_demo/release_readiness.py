from __future__ import annotations


VERIFICATION_COMMANDS = (
    r".\.venv\Scripts\python.exe scripts\verify_eva_public_demo_release.py",
    r".\.venv\Scripts\python.exe scripts\verify_eva_all.py --quick --timeout 90",
    r".\.venv\Scripts\python.exe scripts\verify_eva_all.py --full --timeout 90",
    "git diff --check",
    "git status --short",
)


def release_readiness_text() -> str:
    return "\n".join(
        (
            "Eva release readiness",
            "- Profile state: ready for local public-demo review.",
            "- Publication state: disabled; no external release action is available.",
            "- Verification state: refresh with the documented terminal commands before any readiness claim.",
            "- Documentation state: public overview, demo guide, capability map, safety proof, and limitations are included.",
            "- Safety state: execution and privacy boundaries remain unchanged.",
            "- Next safe step: user-approved commit execution outside Eva or a separate explicit commit-approval phase.",
        )
    )
