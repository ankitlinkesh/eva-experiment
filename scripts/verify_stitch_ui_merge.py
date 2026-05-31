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
    index_path = FRONTEND / "index.html"
    styles_path = FRONTEND / "styles.css"
    app_path = FRONTEND / "app.js"
    failures = 0

    failures += emit("frontend_index_exists", index_path.exists())
    failures += emit("frontend_styles_exists", styles_path.exists())
    failures += emit("frontend_app_exists", app_path.exists())
    if failures:
        return 1

    html = index_path.read_text(encoding="utf-8")
    css = styles_path.read_text(encoding="utf-8")
    js = app_path.read_text(encoding="utf-8")
    combined = "\n".join([html, css, js])

    video_match = re.search(r"<video[^>]*class=\"[^\"]*eva-core-video[^\"]*\"[^>]*>", html, flags=re.IGNORECASE)
    video_tag = video_match.group(0) if video_match else ""
    failures += emit("eva_identity_present", "EVA" in html and "E.V.A" in html)
    failures += emit("jarvis_identity_absent", "jarvis" not in combined.lower())
    failures += emit("stitch_shell_present", "stitch-topbar" in html and "stitch-rail" in html)
    failures += emit("stitch_neural_nodes_present", "Recent neural nodes" in html and "Subsystem logs" in html)
    failures += emit("eva_core_video_reference", "/assets/eva-core-loop.mp4" in html)
    failures += emit("eva_core_video_asset_exists", (FRONTEND / "assets" / "eva-core-loop.mp4").exists())
    failures += emit("video_element_exists", bool(video_match), video_tag=video_tag)
    for attr in ("autoplay", "muted", "loop", "playsinline"):
        failures += emit(f"video_has_{attr}", attr in video_tag.lower())
    failures += emit("video_has_no_controls", "controls" not in video_tag.lower())

    failures += emit("chat_input_exists", 'id="messageInput"' in html and "Ask Eva anything..." in html)
    failures += emit("send_button_exists", 'type="submit"' in html and "Send" in html)
    failures += emit("mic_button_exists", 'id="micButton"' in html)
    failures += emit("voice_toggle_exists", 'id="voiceToggle"' in html)
    failures += emit("brain_dropdown_exists", 'id="brainSelect"' in html)
    expected_brains = [
        "Auto",
        "NVIDIA NIM",
        "Gemini",
        "OpenRouter",
        "Groq",
        "CLōD",
        "Ollama Qwen",
        "Ollama Llama",
        "Local Only",
    ]
    failures += emit("brain_dropdown_options_present", all(option in html for option in expected_brains))
    expected_commands = [
        "use auto brain",
        "use nvidia nim",
        "use gemini",
        "use openrouter",
        "use groq",
        "use clod",
        "use qwen",
        "use llama",
        "use local brain",
    ]
    failures += emit("brain_dropdown_commands_present", all(command in js for command in expected_commands))
    failures += emit("startup_greeting_mentions_ankit", "Yo Ankit, how are you doing today?" in html)
    failures += emit("chat_input_sticky", ".composer" in css and "position: sticky" in css and "bottom: 0" in css)
    failures += emit("messages_scroll_internally", ".message-list" in css and "overflow-y: auto" in css and "min-height: 0" in css)

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
