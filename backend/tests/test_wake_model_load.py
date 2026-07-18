"""The wake model must actually load (Phase 61) — a bug found by live driving.

`detect_wake_word` funnels every failure into "no wake": engine missing, model
file missing, or the engine raising on load all look identical to a quiet room.
Live driving found the wake word could NEVER fire: openWakeWord needs the shared
melspectrogram/embedding preprocessors, looks for them inside its OWN package
directory, and ignores the configured model dir — so keeping models off the
system drive made it raise NO_SUCHFILE on every load, silently. Status
meanwhile reported engine_installed=True and model_present=True.

These tests are environment-independent on purpose: they build a fake model dir
and a fake engine, so they hold whether or not the real models are installed.
"""
from __future__ import annotations

import pytest

from backend.eva.voice import wake


@pytest.fixture(autouse=True)
def _clean_model_cache():
    wake.reset_wake_state()
    yield
    wake.reset_wake_state()


def _model_dir(tmp_path, *, with_preprocessors: bool):
    (tmp_path / "hey_jarvis_v0.1.onnx").write_bytes(b"fake-wake-model")
    if with_preprocessors:
        for name in wake.PREPROCESSOR_MODELS:
            (tmp_path / name).write_bytes(b"fake-preprocessor")
    return {"EVA_VOICE_INPUT_ENABLED": "1", "EVA_WAKE_MODEL_DIR": str(tmp_path)}


def _fake_engine(monkeypatch, captured: dict):
    import openwakeword.model as engine

    class FakeModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(engine, "Model", FakeModel)


def test_preprocessor_paths_are_passed_to_the_engine(monkeypatch, tmp_path):
    """The regression guard: without these kwargs the engine loads nothing."""
    captured: dict = {}
    _fake_engine(monkeypatch, captured)
    env = _model_dir(tmp_path, with_preprocessors=True)

    assert wake._load_model(env) is not None
    assert captured["melspec_model_path"] == str(tmp_path / "melspectrogram.onnx")
    assert captured["embedding_model_path"] == str(tmp_path / "embedding_model.onnx")
    assert wake.last_load_error() == ""


def test_missing_preprocessors_are_reported_not_silent(monkeypatch, tmp_path):
    """A dead wake word must be diagnosable, not look like silence."""
    env = _model_dir(tmp_path, with_preprocessors=False)
    assert wake.preprocessors_present(env) is False

    status = wake.wake_status(env)
    assert status["model_present"] is True       # the wake model IS there ...
    assert status["preprocessors_present"] is False  # ... but this is what was missing
    assert status["ready"] is False              # so the stack is honestly NOT ready


def test_status_reports_ready_when_everything_is_present(monkeypatch, tmp_path):
    env = _model_dir(tmp_path, with_preprocessors=True)
    monkeypatch.setattr(wake, "wake_status", wake.wake_status)  # no-op, keep real
    status = wake.wake_status(env)
    assert status["preprocessors_present"] is True
    # "ready" also needs the engine installed, which it is in this repo's venv.
    assert status["ready"] is status["engine_installed"]


def test_load_failure_is_recorded_for_diagnosis(monkeypatch, tmp_path):
    import openwakeword.model as engine

    class ExplodingModel:
        def __init__(self, **kwargs):
            raise RuntimeError("NO_SUCHFILE: melspectrogram.onnx")

    monkeypatch.setattr(engine, "Model", ExplodingModel)
    env = _model_dir(tmp_path, with_preprocessors=True)

    assert wake._load_model(env) is None
    # The failure is captured rather than swallowed into an indistinguishable None.
    assert "NO_SUCHFILE" in wake.last_load_error()


def test_detection_never_raises_when_the_model_is_unavailable(monkeypatch, tmp_path):
    import openwakeword.model as engine

    monkeypatch.setattr(engine, "Model", lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    env = _model_dir(tmp_path, with_preprocessors=True)
    # A broken model must mean "no wake", never an exception into the mic loop.
    assert wake.detect_wake_word([0] * 1280, env).detected is False
