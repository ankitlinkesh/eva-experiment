from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def emit(case: str, passed: bool, **payload: object) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=False))
    return 0 if passed else 1


def main() -> int:
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    css = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    js = (FRONTEND / "app.js").read_text(encoding="utf-8")
    combined = "\n".join([html, css, js])
    failures = 0

    video_match = re.search(r"<video[^>]*class=\"[^\"]*eva-core-video[^\"]*\"[^>]*>", html, flags=re.IGNORECASE)
    video_tag = video_match.group(0) if video_match else ""
    failures += emit("video_element_exists", bool(video_match), video_tag=video_tag)
    for attr in ("autoplay", "muted", "loop", "playsinline"):
        failures += emit(f"video_has_{attr}", attr in video_tag.lower())

    failures += emit("mp4_source_path_present", "/assets/eva-core-loop.mp4" in html)
    failures += emit("webm_source_path_present", "/assets/eva-core-loop.webm" in html)
    failures += emit("mp4_asset_exists", (FRONTEND / "assets" / "eva-core-loop.mp4").exists())

    failures += emit("two_sections_exist", "eva-hero" in html and "command-deck" in html)
    failures += emit("open_command_deck_button_exists", "Open Command Deck" in html and "#commandDeck" in html)
    failures += emit("brain_dropdown_exists", 'id="brainSelect"' in html and "NVIDIA NIM" in html and "Local Only" in html)
    failures += emit("chat_input_exists", 'id="messageInput"' in html and "Ask Eva anything..." in html)
    failures += emit("mic_button_exists", 'id="micButton"' in html)
    failures += emit("startup_greeting_mentions_ankit", "Yo Ankit, how are you doing today?" in html)
    failures += emit("assistant_name_is_eva", "E.V.A" in html and "EVA" in html)
    failures += emit("jarvis_identity_absent", "jarvis" not in combined.lower())

    failures += emit("chat_input_sticky_css", ".composer" in css and "position: sticky" in css and "bottom: 0" in css)
    failures += emit("message_list_internal_scroll", ".message-list" in css and "overflow-y: auto" in css and "min-height: 0" in css)
    failures += emit("video_visibility_script_exists", "visibilitychange" in js and "evaCoreVideo" in js)
    failures += emit("brain_command_script_exists", "use nvidia nim" in js and "use local brain" in js)

    secret_patterns = [
        r"AIza[0-9A-Za-z_\-]{20,}",
        r"sk-or-v1-[0-9A-Za-z_\-]+",
        r"nvapi-[0-9A-Za-z_\-]+",
        r"tvly-[0-9A-Za-z_\-]+",
    ]
    leaked = [pattern for pattern in secret_patterns if re.search(pattern, combined)]
    failures += emit("no_hardcoded_api_keys", not leaked, leaked_patterns=leaked)

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
