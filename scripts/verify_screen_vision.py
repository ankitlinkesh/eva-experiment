from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Eva Gemini Vision screen analysis.")
    parser.add_argument("--capture", action="store_true", help="Capture one screenshot and analyze it.")
    parser.add_argument("--simulate-429", action="store_true", help="Simulate a Gemini Vision 429 and verify local blocking.")
    args = parser.parse_args()

    load_env(ROOT / ".env")

    has_key = bool(os.environ.get("GEMINI_API_KEY"))
    enabled = os.environ.get("VISION_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    model = os.environ.get("GEMINI_VISION_MODEL") or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"

    print(f"vision_enabled={enabled}")
    print(f"gemini_key_configured={has_key}")
    print(f"vision_model={model}")

    nested_ok = verify_nested_json_summary()
    print(f"nested_json_summary_clean={nested_ok}")
    if not nested_ok:
        return 1

    if args.simulate_429:
        return simulate_429()

    if not enabled:
        print("warning=vision_disabled")
        return 0
    if not has_key:
        print("warning=missing_gemini_api_key")
        return 0
    if not args.capture:
        print("capture_skipped=true")
        print("pass=true")
        return 0

    from backend.eva.tools.registry import ToolRegistry

    registry = ToolRegistry()
    result = registry.run("analyze_screen", question="Tell me what is visible on this screen and mention any obvious issue.")
    print(f"ok={bool(result.get('ok'))}")
    print(f"provider={result.get('provider')}")
    print(f"model={result.get('model')}")
    if result.get("ok"):
        print(f"summary={str(result.get('summary') or '')[:500]}")
        possible_issue = str(result.get("possible_issue") or "").strip()
        if possible_issue:
            print(f"possible_issue={possible_issue[:500]}")
        actions = result.get("suggested_actions") or []
        if isinstance(actions, list):
            print(f"suggested_actions_count={len(actions)}")
    else:
        print(f"error={result.get('error')}")
    return 0 if result.get("ok") else 1


def verify_nested_json_summary() -> bool:
    from backend.eva.vision import screen_vision

    inner = {
        "summary": "A terminal window is open.",
        "detected_text": "PowerShell",
        "possible_issue": "",
        "suggested_actions": ["Continue from the prompt."],
    }
    outer_as_string = json.dumps(inner)
    result = screen_vision._normalize_success("gemini-2.5-flash", json.dumps(outer_as_string))
    return (
        result.get("summary") == "A terminal window is open."
        and result.get("detected_text") == "PowerShell"
        and "{" not in str(result.get("summary"))
    )


def simulate_429() -> int:
    from backend.eva.vision import screen_vision

    png_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    class FakeResponse:
        status_code = 429
        headers = {"Retry-After": "60"}

        def json(self) -> dict[str, object]:
            return {}

    class FakeClient:
        calls = 0

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, *args: object, **kwargs: object) -> FakeResponse:
            type(self).calls += 1
            return FakeResponse()

    old_client = screen_vision.httpx.Client
    old_state_path = screen_vision.VISION_STATE_PATH
    old_key = os.environ.get("GEMINI_API_KEY")
    old_enabled = os.environ.get("VISION_ENABLED")
    old_model = os.environ.get("GEMINI_VISION_MODEL")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            image = tmp_path / "screen.png"
            image.write_bytes(png_1x1)
            screen_vision.VISION_STATE_PATH = tmp_path / "vision_usage_state.json"
            screen_vision.httpx.Client = FakeClient  # type: ignore[assignment]
            os.environ["GEMINI_API_KEY"] = "configured-for-simulation-only"
            os.environ["VISION_ENABLED"] = "true"
            os.environ["GEMINI_VISION_MODEL"] = "gemini-2.5-flash"

            first = screen_vision.analyze_screen_image_sync(str(image), "simulate 429")
            calls_after_first = FakeClient.calls
            second = screen_vision.analyze_screen_image_sync(str(image), "should skip")
            calls_after_second = FakeClient.calls
            status = screen_vision.vision_status()

            blocked_until = int((status.get("usage") or {}).get("blocked_until") or 0)
            skipped_before_call = calls_after_first == 1 and calls_after_second == 1
            pass_value = (
                first.get("error", "").startswith("vision_blocked_until:")
                and second.get("error", "").startswith("vision_blocked_until:")
                and bool(first.get("rate_limited"))
                and bool(second.get("rate_limited"))
                and blocked_until > 0
                and skipped_before_call
            )

            print("simulate_429=true")
            print(f"first_error={first.get('error')}")
            print(f"second_error={second.get('error')}")
            print(f"blocked_until_set={blocked_until > 0}")
            print(f"skipped_before_call={skipped_before_call}")
            print(f"http_calls={calls_after_second}")
            print(f"pass={pass_value}")
            return 0 if pass_value else 1
    finally:
        screen_vision.httpx.Client = old_client  # type: ignore[assignment]
        screen_vision.VISION_STATE_PATH = old_state_path
        if old_key is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = old_key
        if old_enabled is None:
            os.environ.pop("VISION_ENABLED", None)
        else:
            os.environ["VISION_ENABLED"] = old_enabled
        if old_model is None:
            os.environ.pop("GEMINI_VISION_MODEL", None)
        else:
            os.environ["GEMINI_VISION_MODEL"] = old_model


if __name__ == "__main__":
    raise SystemExit(main())
