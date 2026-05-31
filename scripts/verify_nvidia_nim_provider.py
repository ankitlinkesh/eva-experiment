from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.core.config import load_project_env, load_settings
from backend.eva.core.fast_commands import maybe_handle_fast_command
from backend.eva.llm.providers.nvidia_nim import NvidiaNIMProvider, nvidia_nim_models_for_purpose
from backend.eva.llm.router import complete_with_fallback, get_llm_status, provider_order
from backend.eva.tools.registry import ToolRegistry


def emit(case: str, passed: bool, **payload: object) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=False))
    return 0 if passed else 1


async def main() -> int:
    load_project_env(ROOT)
    settings = load_settings(ROOT / "config" / "eva.toml")
    failures = 0

    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    nim_key_lines = [line for line in env_example.splitlines() if line.startswith("NVIDIA_NIM") and "API_KEY" in line]
    failures += emit(
        "env_example_has_one_nim_api_key_variable",
        nim_key_lines == ["NVIDIA_NIM_API_KEY="],
        nim_key_lines=nim_key_lines,
    )
    for required in (
        "NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1",
        "NVIDIA_NIM_MODEL=nvidia/nemotron-3-nano-30b-a3b",
        "NVIDIA_NIM_FALLBACK_MODELS=openai/gpt-oss-120b,deepseek-ai/deepseek-v4-flash",
        "NVIDIA_NIM_PLANNER_MODEL=nvidia/nemotron-3-nano-30b-a3b",
        "NVIDIA_NIM_TTS_MODEL=nvidia/magpie-tts-zeroshot",
    ):
        failures += emit(f"env_placeholder_{required.split('=')[0].lower()}", required in env_example)

    import tempfile

    original_probe = os.environ.get("EVA_ENV_LOCAL_PROBE")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        (tmp_root / ".env").write_text("EVA_ENV_LOCAL_PROBE=from_env\n", encoding="utf-8")
        (tmp_root / ".env.local").write_text("EVA_ENV_LOCAL_PROBE=from_env_local\n", encoding="utf-8")
        os.environ.pop("EVA_ENV_LOCAL_PROBE", None)
        load_project_env(tmp_root)
        failures += emit(
            "env_local_overrides_env",
            os.environ.get("EVA_ENV_LOCAL_PROBE") == "from_env_local",
        )
    if original_probe is None:
        os.environ.pop("EVA_ENV_LOCAL_PROBE", None)
    else:
        os.environ["EVA_ENV_LOCAL_PROBE"] = original_probe

    original_order = os.environ.get("EVA_CLOUD_PROVIDER_ORDER")
    original_key = os.environ.get("NVIDIA_NIM_API_KEY")
    original_ollama_planner = os.environ.get("EVA_USE_OLLAMA_FOR_PLANNER")
    original_gemini_keys = {
        name: os.environ.get(name)
        for name in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5", "GEMINI_API_KEY_6", "GEMINI_API_KEYS"]
    }
    os.environ["EVA_CLOUD_PROVIDER_ORDER"] = "nvidia_nim,gemini,openrouter,groq,clod,ollama"
    os.environ.pop("NVIDIA_NIM_API_KEY", None)

    order = provider_order()
    failures += emit(
        "provider_order_starts_with_nvidia_nim",
        order[:6] == ["nvidia_nim", "gemini", "openrouter", "groq", "clod", "ollama"],
        provider_order=order,
    )

    provider = NvidiaNIMProvider(settings.models)
    failures += emit("nim_provider_skips_when_key_missing", provider.available() is False, model=provider.model)

    os.environ["EVA_CLOUD_PROVIDER_ORDER"] = "nvidia_nim,gemini"
    os.environ["EVA_USE_OLLAMA_FOR_PLANNER"] = "false"
    for key_name in original_gemini_keys:
        os.environ.pop(key_name, None)
    routed_fallthrough = await complete_with_fallback(
        [{"role": "user", "content": "Return JSON."}],
        settings.models,
        purpose="planner",
        temperature=0.1,
        max_tokens=50,
    )
    fallthrough_attempts = [attempt.__dict__ for attempt in routed_fallthrough.attempts]
    failures += emit(
        "router_falls_through_from_missing_nim_to_gemini",
        len(fallthrough_attempts) >= 2
        and fallthrough_attempts[0].get("provider") == "nvidia_nim"
        and fallthrough_attempts[0].get("error") == "missing_api_key"
        and fallthrough_attempts[1].get("provider") == "gemini"
        and fallthrough_attempts[1].get("error") == "missing_api_key",
        providers_tried=[{"provider": item.get("provider"), "error": item.get("error")} for item in fallthrough_attempts],
    )

    status = get_llm_status(settings.models)
    nim_status = status.get("nvidia_nim") or {}
    failures += emit(
        "llm_status_shows_nim_without_key",
        status.get("configured_keys", {}).get("nvidia_nim") is False
        and "api_key" not in json.dumps(status).lower()
        and nim_status.get("base_url") == "https://integrate.api.nvidia.com/v1",
        nim_status=nim_status,
    )

    os.environ["EVA_CLOUD_PROVIDER_ORDER"] = "nvidia_nim"
    routed = await complete_with_fallback(
        [{"role": "user", "content": "Say hello in one short sentence."}],
        settings.models,
        purpose="final_response",
        temperature=0.1,
        max_tokens=50,
    )
    attempts = [attempt.__dict__ for attempt in routed.attempts]
    nim_attempts = [attempt for attempt in attempts if attempt.get("provider") == "nvidia_nim"]
    failures += emit(
        "router_records_nim_missing_key_attempt",
        bool(nim_attempts) and all(item.get("error") == "missing_api_key" for item in nim_attempts),
        nim_attempts=nim_attempts,
    )

    planner_models = nvidia_nim_models_for_purpose("planner")
    failures += emit(
        "nim_planner_models_deduped_and_ordered",
        planner_models[:3] == ["nvidia/nemotron-3-nano-30b-a3b", "openai/gpt-oss-120b", "deepseek-ai/deepseek-v4-flash"],
        planner_models=planner_models,
    )

    command = maybe_handle_fast_command("llm status", ToolRegistry())
    failures += emit(
        "llm_status_fast_command_mentions_nim_safely",
        command is not None and "nvidia_nim" in command[0] and "NVIDIA_NIM_API_KEY" not in command[0],
        response_preview=(command[0][:1000] if command else ""),
    )

    if original_order is None:
        os.environ.pop("EVA_CLOUD_PROVIDER_ORDER", None)
    else:
        os.environ["EVA_CLOUD_PROVIDER_ORDER"] = original_order
    if original_key is None:
        os.environ.pop("NVIDIA_NIM_API_KEY", None)
    else:
        os.environ["NVIDIA_NIM_API_KEY"] = original_key
    if original_ollama_planner is None:
        os.environ.pop("EVA_USE_OLLAMA_FOR_PLANNER", None)
    else:
        os.environ["EVA_USE_OLLAMA_FOR_PLANNER"] = original_ollama_planner
    for key_name, key_value in original_gemini_keys.items():
        if key_value is None:
            os.environ.pop(key_name, None)
        else:
            os.environ[key_name] = key_value

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
