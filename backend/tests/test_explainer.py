"""Executable spec for the isolated action explainer (Phase 75).

An approval prompt that shows a tool name and an argument dict is precise and
not always legible, and the moment a person approves things they do not
understand, every gate above becomes decoration.

Two properties carry the safety here, and both are about what the GENERATED
half cannot do:

  * The deterministic half is assembled from source of truth with no model
    involved, so nothing can talk it into saying something false. It is always
    present, and a user who reads only that half has lost nothing.
  * The generated half sees ONLY the action -- never the conversation -- and is
    handed `tools=None`, so a successful attack on it achieves at most a
    misleading sentence printed beneath an accurate description of exactly what
    will run.

No test here performs a network call: `explain_action` is pure, and the
generated path is faked.
"""

from __future__ import annotations

import pytest

from eva.agents.explainer import ActionExplanation, explain_action, generate_explanation
from eva.mcp.runner import run_async
from eva.security.action_types import ActionType


class TestDeterministicHalf:
    def test_is_pure_and_needs_no_model(self) -> None:
        """No network, no provider, no key -- an approval must be reviewable
        even when every LLM provider is down."""
        result = explain_action(
            tool="file.delete",
            description="Delete a file.",
            action_type="DESTRUCTIVE_FILE_ACTION",
            decision="override",
            args={"path": "notes.txt"},
        )
        assert result.generated is None
        assert "Delete a file." in result.what_it_does

    def test_shows_the_command_verbatim(self) -> None:
        """The anchor. The action being explained is untrusted input, so the
        raw call must always be visible rather than only a description of it."""
        result = explain_action("file.delete", "Delete a file.", "DESTRUCTIVE_FILE_ACTION", "override", {"path": "x.txt"})
        assert "file.delete" in result.command_line
        assert "x.txt" in result.command_line
        assert "file.delete" in result.as_text()

    def test_explains_the_tier_difference(self) -> None:
        confirm = explain_action("message.prepare", "Draft a message.", "SAFE_LOCAL_UI", "confirm")
        override = explain_action("file.delete", "Delete a file.", "DESTRUCTIVE_FILE_ACTION", "override")
        assert "confirmation" in confirm.approval_meaning.lower()
        assert "override" in override.approval_meaning.lower()
        assert confirm.approval_meaning != override.approval_meaning

    def test_says_what_happens_if_declined(self) -> None:
        result = explain_action("file.delete", "Delete a file.", "DESTRUCTIVE_FILE_ACTION", "override")
        assert "will not run" in result.if_declined

    @pytest.mark.parametrize("action_type", [item.value for item in ActionType])
    def test_every_action_type_has_plain_language(self, action_type: str) -> None:
        """A new ActionType must not silently produce a blank explanation."""
        result = explain_action("t", "d", action_type, "confirm")
        assert result.why_gated.strip()
        assert action_type in result.why_gated

    def test_unknown_action_type_degrades_readably(self) -> None:
        result = explain_action("t", "d", "SOMETHING_NEW", "confirm")
        assert "SOMETHING_NEW" in result.why_gated

    def test_missing_description_is_stated_not_blank(self) -> None:
        result = explain_action("t", "", "SAFE_LOCAL_READ", "confirm")
        assert result.what_it_does.strip()


class TestSecrets:
    def test_renders_only_what_it_is_given(self) -> None:
        """The caller passes the MASKED payload. This asserts the explainer
        does not go looking for the real value -- an explanation must never be
        the thing that prints what the ledger was careful to hide."""
        result = explain_action(
            "screen.type_text",
            "Type text.",
            "SAFE_LOCAL_UI",
            "confirm",
            args={"text": "[HIDDEN]"},
        )
        assert "[HIDDEN]" in result.command_line
        assert "hunter2" not in result.as_text()


class TestGeneratedHalf:
    def test_failure_degrades_instead_of_blocking(self, monkeypatch) -> None:
        """A provider outage must never make an action unreviewable."""

        async def _boom(*args, **kwargs):
            raise RuntimeError("provider down")

        monkeypatch.setattr("eva.llm.router.complete_with_fallback", _boom)
        base = explain_action("file.delete", "Delete a file.", "DESTRUCTIVE_FILE_ACTION", "override")
        result = run_async(generate_explanation(base))
        assert result.generated is None
        assert result.generated_error is not None
        # The deterministic half survives intact.
        assert "file.delete" in result.as_text()
        assert "will not run" in result.as_text()

    def test_generated_text_is_labelled_as_generated(self, monkeypatch) -> None:
        """It must never read as authoritative: it is a summary of untrusted
        input, produced by a model that could have been misled by it."""

        class _Resp:
            text = "This deletes a file permanently."
            ok = True

        class _Routed:
            response = _Resp()

        async def _ok(*args, **kwargs):
            return _Routed()

        monkeypatch.setattr("eva.llm.router.complete_with_fallback", _ok)
        base = explain_action("file.delete", "Delete a file.", "DESTRUCTIVE_FILE_ACTION", "override")
        text = run_async(generate_explanation(base)).as_text()
        assert "This deletes a file permanently." in text
        assert "generated" in text.lower()
        assert "no access to this" in text.lower()

    def test_is_called_with_no_tools_and_no_conversation(self, monkeypatch) -> None:
        """The isolation, asserted rather than promised.

        `tools=None` is what makes the explainer unable to act; the message list
        containing only the action is what makes it unable to be steered by
        anything said earlier in a chat.
        """
        seen: dict = {}

        class _Resp:
            text = "ok"
            ok = True

        class _Routed:
            response = _Resp()

        async def _capture(messages, settings, **kwargs):
            seen["messages"] = messages
            seen["kwargs"] = kwargs
            return _Routed()

        monkeypatch.setattr("eva.llm.router.complete_with_fallback", _capture)
        base = explain_action("file.delete", "Delete a file.", "DESTRUCTIVE_FILE_ACTION", "override", {"path": "x"})
        run_async(generate_explanation(base))

        assert seen["kwargs"]["tools"] is None
        roles = [m["role"] for m in seen["messages"]]
        assert roles == ["system", "user"]

        # The user turn is reconstructed from the deterministic fields and
        # nothing else. Asserted structurally rather than by keyword: an
        # earlier version of this test looked for the absence of the word
        # "history" and failed against correct code, because the SYSTEM prompt
        # legitimately says "you have no conversation history".
        user = seen["messages"][1]["content"]
        prefixes = [line.split(":", 1)[0] for line in user.splitlines() if line.strip()]
        assert prefixes == ["Action", "Declared purpose", "Classification"]
        assert "file.delete" in user

    def test_empty_model_output_is_reported_not_silent(self, monkeypatch) -> None:
        class _Resp:
            text = "   "
            ok = True

        class _Routed:
            response = _Resp()

        async def _empty(*args, **kwargs):
            return _Routed()

        monkeypatch.setattr("eva.llm.router.complete_with_fallback", _empty)
        base = explain_action("t", "d", "SAFE_LOCAL_READ", "confirm")
        result = run_async(generate_explanation(base))
        assert result.generated is None
        assert result.generated_error


class TestRendering:
    def test_can_render_without_the_generated_half(self) -> None:
        base = ActionExplanation(
            tool="t",
            command_line="t()",
            what_it_does="does a thing",
            why_gated="because",
            approval_meaning="confirm it",
            if_declined="it will not run",
            generated="a generated sentence",
        )
        text = base.as_text(include_generated=False)
        assert "a generated sentence" not in text
        assert "does a thing" in text
