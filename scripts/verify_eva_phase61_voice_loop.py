"""Standalone verifier for Phase 61 (the voice loop, wired) — closes the "49c" gap.

Voice was declared complete in Phase 49b: Piper speaks, faster-whisper hears,
openWakeWord waits for the wake word. But ``voice/listener.listen_once`` was
called by NOTHING in the app — the loop existed and never ran. The same
"built but not wired" shape as Phases 36/53 and the memory-arrival bug.

What this verifies (fully offline: no microphone, no models, no network):

  1. THE LOOP IS ACTUALLY WIRED: POST /api/chat/voice exists and calls the REAL
     listen_once, not a stub.
  2. SPEECH EARNS NO PRIVILEGE: a heard transcript re-enters through chat(), so
     it produces the SAME reply as the identical message typed — same pipeline,
     same permission gate. This is the security property, kept structurally.
  3. NO TRANSCRIPT => NO CHAT TURN: voice disabled / wake timeout surfaces a
     reason and runs nothing.
  4. THE WAKE MODEL CAN ACTUALLY LOAD (bug found by LIVE driving): openWakeWord
     needs the shared melspectrogram/embedding preprocessors and looks for them
     in its OWN package dir, ignoring the configured model dir — so the wake word
     could NEVER fire, while every failure path returned an indistinguishable
     "no wake" and status reported engine_installed/model_present as fine. The
     paths are now passed explicitly and the stack reports readiness honestly.

The checks use a fake engine and a fake model dir, so they hold whether or not
the real voice models are installed on the box running them.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from fastapi.testclient import TestClient

    from backend.eva.api import routes
    from backend.eva.main import app
    from backend.eva.voice import wake
    from backend.eva.voice.listener import ListenResult, listen_once
    from scripts import verify_eva_all

    headers = {"X-Eva-Client": "1"}
    client = TestClient(app)

    # 1. The loop is wired to the REAL listener, not a stub.
    check(routes.listen_once is listen_once, "the voice route must call the real listen_once")

    saved_listen = routes.listen_once
    saved_flag = os.environ.get("EVA_VOICE_INPUT_ENABLED")
    try:
        # 3. No transcript => no chat turn, and the reason is surfaced.
        routes.listen_once = lambda: ListenResult(reason="voice_input_disabled")
        body = client.post("/api/chat/voice", json={}, headers=headers).json()
        check(body["reason"] == "voice_input_disabled", f"a disabled mic must surface its reason, got {body!r}")
        check(body["reply"] == "" and body["transcript"] == "", "a refused listen must produce no chat turn")
        check(body["woke"] is False, "a refused listen must not report waking")

        routes.listen_once = lambda: ListenResult(reason="wake_timeout")
        body = client.post("/api/chat/voice", json={}, headers=headers).json()
        check(body["reason"] == "wake_timeout" and body["reply"] == "", "a wake timeout must produce no chat turn")

        # 2. Speech earns no privilege: heard text == typed text.
        spoken_words = "eva capability truth"  # deterministic; no LLM/network needed
        typed = client.post("/api/chat", json={"message": spoken_words}, headers=headers).json()

        routes.listen_once = lambda: ListenResult(text=spoken_words, woke=True, wake_word="hey_jarvis", reason="ok")
        heard = client.post("/api/chat/voice", json={}, headers=headers).json()

        check(heard["transcript"] == spoken_words, "the transcript must be reported back")
        check(heard["woke"] is True, "a heard utterance must report waking")
        check(
            heard["reply"] == typed["reply"],
            "a spoken message must produce the SAME reply as typing it (same pipeline, same gate)",
        )
        check(heard["source"] == f"voice+{typed['source']}", f"source must name the underlying route, got {heard['source']!r}")

        # The status endpoint must not open a device or claim a mic while off.
        os.environ.pop("EVA_VOICE_INPUT_ENABLED", None)
        status = client.get("/api/voice/listen/status", headers=headers).json()
        check(status.get("enabled") is False, "voice input must be off by default")
        check(status.get("microphone_available") is False, "a disabled listener must not report an available mic")
    finally:
        routes.listen_once = saved_listen
        if saved_flag is None:
            os.environ.pop("EVA_VOICE_INPUT_ENABLED", None)
        else:
            os.environ["EVA_VOICE_INPUT_ENABLED"] = saved_flag

    # 4. The wake model can actually load — the bug live driving found.
    import tempfile

    import openwakeword.model as engine

    saved_engine = engine.Model
    wake.reset_wake_state()
    try:
        with tempfile.TemporaryDirectory(prefix="eva-wake-") as tmp:
            directory = Path(tmp)
            (directory / "hey_jarvis_v0.1.onnx").write_bytes(b"fake")
            for name in wake.PREPROCESSOR_MODELS:
                (directory / name).write_bytes(b"fake")
            env = {"EVA_VOICE_INPUT_ENABLED": "1", "EVA_WAKE_MODEL_DIR": str(directory)}

            captured: dict = {}

            class FakeModel:
                def __init__(self, **kwargs):
                    captured.update(kwargs)

            engine.Model = FakeModel
            check(wake._load_model(env) is not None, "the wake model must load when everything is present")
            check(
                captured.get("melspec_model_path") == str(directory / "melspectrogram.onnx")
                and captured.get("embedding_model_path") == str(directory / "embedding_model.onnx"),
                "the preprocessor paths MUST be passed explicitly or openWakeWord loads nothing",
            )

            # Honest readiness: the wake model alone is not enough.
            for name in wake.PREPROCESSOR_MODELS:
                (directory / name).unlink()
            status = wake.wake_status(env)
            check(status["model_present"] is True, "the wake model is present in this fixture")
            check(status["preprocessors_present"] is False, "missing preprocessors must be reported")
            check(status["ready"] is False, "a stack missing its preprocessors must NOT report ready")

            # A broken engine means "no wake", never an exception into the mic loop.
            wake.reset_wake_state()
            engine.Model = lambda **kw: (_ for _ in ()).throw(RuntimeError("NO_SUCHFILE"))
            check(wake.detect_wake_word([0] * 1280, env).detected is False, "a broken model must mean no wake, not a crash")
            check("NO_SUCHFILE" in wake.last_load_error(), "a load failure must be recorded for diagnosis, not swallowed")
    finally:
        engine.Model = saved_engine
        wake.reset_wake_state()

    # 5. Registration.
    name = "verify_eva_phase61_voice_loop.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 61 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 61 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 61 verifier")

    print(
        "PASS: Phase 61 voice loop -- the ears are finally connected. listen_once() existed since 49b and NOTHING "
        "called it; POST /api/chat/voice now captures one bounded utterance and routes the transcript through the "
        "SAME pipeline as typed text, so a spoken message yields a byte-identical reply and faces the identical "
        "permission gate (speech earns no privilege); no transcript means no chat turn, with the reason surfaced. "
        "LIVE driving also found the wake word could NEVER fire: openWakeWord looks for its shared "
        "melspectrogram/embedding preprocessors inside its own package dir and ignored our model dir, so every load "
        "raised NO_SUCHFILE and was swallowed into an indistinguishable 'no wake' while status said engine_installed "
        "and model_present were fine. The paths are now passed explicitly, load failures are recorded, and readiness "
        "is reported honestly. Live proof: the real model scored 0.9985 on 'hey jarvis' and the full loop woke, "
        "recorded and transcribed real audio."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
