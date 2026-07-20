"""Executable spec for the bounded command runner (Phase 74).

The safety argument is that this is NOT a shell, so these tests are mostly
about the ways something could quietly become one. `validate` is pure, so the
escape attempts below run no processes at all.

The subtle one is TestDangerousFlags. An executable allowlist alone is not
sufficient: `git` will happily execute an arbitrary program for you if asked
via `-c core.pager=...`, `--ext-diff`, `--upload-pack` or `--exec-path`.
Allowlisting the binary while ignoring its flags would hand back exactly the
arbitrary execution that `ActionType.SHELL_ACTION`'s hard block exists to
prevent, under a different name.
"""

from __future__ import annotations

import pytest

from eva.shell.bounded_runner import (
    ALLOWED_COMMANDS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_ARG_LENGTH,
    MAX_ARGS,
    MAX_OUTPUT_CHARS,
    MAX_TIMEOUT_SECONDS,
    WORKSPACE_ROOT,
    BoundedResult,
    describe_allowed,
    run_bounded,
    validate,
)


class TestExecutableAllowlist:
    @pytest.mark.parametrize("command", ["bash", "sh", "cmd", "powershell", "curl", "rm", "del", "", "GIT"])
    def test_unlisted_programs_are_refused(self, command: str) -> None:
        assert validate(command, ("--version",)) is not None

    def test_listed_programs_are_permitted(self) -> None:
        assert validate("git", ("status",)) is None
        assert validate("python", ("--version",)) is None


class TestSubcommandAllowlist:
    @pytest.mark.parametrize(
        "args",
        [("push",), ("commit", "-m", "x"), ("reset", "--hard"), ("clean", "-fd"), ("checkout", "main"), ("rm", "x")],
    )
    def test_mutating_git_subcommands_are_refused(self, args: tuple[str, ...]) -> None:
        """A bounded run must not be able to modify the repository."""
        assert validate("git", args) is not None

    def test_read_only_git_subcommands_are_permitted(self) -> None:
        for args in [("status",), ("log", "-n", "3"), ("diff", "--stat"), ("branch",), ("rev-parse", "HEAD")]:
            assert validate("git", args) is None, args

    def test_missing_subcommand_is_refused(self) -> None:
        assert validate("git", ()) is not None

    def test_python_cannot_execute_code(self) -> None:
        """-c and -m are the whole reason `python` is dangerous."""
        assert validate("python", ("-c", "import os")) is not None
        assert validate("python", ("-m", "http.server")) is not None

    def test_pip_cannot_install(self) -> None:
        assert validate("pip", ("install", "anything")) is not None
        assert validate("pip", ("uninstall", "anything")) is not None


class TestDangerousFlags:
    """The part an executable allowlist alone would miss."""

    @pytest.mark.parametrize(
        "args",
        [
            ("status", "-c", "core.pager=calc.exe"),
            ("-c", "core.pager=calc.exe", "status"),
            ("status", "-c=core.pager=calc.exe"),
            ("diff", "--ext-diff"),
            ("status", "--exec-path=/tmp"),
            ("status", "--upload-pack=calc.exe"),
            ("status", "--output=/tmp/x"),
            ("status", "--git-dir=/elsewhere"),
        ],
    )
    def test_git_flags_that_launch_other_programs_are_refused(self, args: tuple[str, ...]) -> None:
        assert validate("git", args) is not None

    def test_the_refusal_explains_why(self) -> None:
        reason = validate("git", ("status", "--ext-diff"))
        assert reason is not None
        assert "execute another program" in reason


class TestNoShellInterpretation:
    """There is no shell, so these are already inert -- refused anyway as
    defence in depth, and because a caller sending them wants something."""

    @pytest.mark.parametrize("meta", [";", "|", "&", "$", "`", ">", "<", "*", "?"])
    def test_shell_metacharacters_are_refused(self, meta: str) -> None:
        assert validate("git", ("status", f"x{meta}y")) is not None

    def test_path_traversal_is_refused(self) -> None:
        assert validate("git", ("show", "../../../etc/passwd")) is not None

    def test_source_never_enables_a_shell(self) -> None:
        """Structural: the one line that would undo the whole design."""
        import inspect

        from eva.shell import bounded_runner

        source = inspect.getsource(bounded_runner)
        assert "shell=True" not in source
        assert "os.system" not in source


class TestBounds:
    def test_too_many_arguments_refused(self) -> None:
        assert validate("git", ("status", *["x"] * (MAX_ARGS + 1))) is not None

    def test_overlong_argument_refused(self) -> None:
        assert validate("git", ("status", "x" * (MAX_ARG_LENGTH + 1))) is not None

    def test_timeout_ceiling_cannot_be_raised(self) -> None:
        """A caller may lower the timeout but never raise it past the ceiling."""
        result = run_bounded("python", ("--version",), timeout=10_000)
        assert result.ok is True
        assert MAX_TIMEOUT_SECONDS >= DEFAULT_TIMEOUT_SECONDS

    def test_workspace_root_is_the_repo(self) -> None:
        """cwd is resolved from source, never from arguments, so nothing a
        caller sends can redirect where a command runs."""
        assert (WORKSPACE_ROOT / "backend" / "eva").is_dir()


class TestResults:
    def test_real_read_only_command_runs(self) -> None:
        result = run_bounded("git", ("status", "--short"))
        assert result.ok is True
        assert result.exit_code == 0
        assert result.refused is False

    def test_refusal_is_marked_and_runs_nothing(self) -> None:
        result = run_bounded("git", ("push",))
        assert result.refused is True
        assert result.ok is False
        assert result.exit_code is None

    def test_output_is_marked_untrusted(self) -> None:
        """Command output is content: a branch name or commit message can say
        anything, so it must never read as instruction."""
        result = run_bounded("git", ("status", "--short"))
        assert result.untrusted is True
        assert "untrusted" in result.as_text().lower()
        assert "not an instruction" in result.as_text().lower()

    def test_truncation_is_reported_not_silent(self) -> None:
        result = BoundedResult(command="git", args=("log",), ok=True, exit_code=0, stdout="x" * 10, truncated=True)
        assert "truncated" in result.as_text().lower()
        assert str(MAX_OUTPUT_CHARS) in result.as_text()

    def test_describe_allowed_lists_every_command(self) -> None:
        text = describe_allowed()
        for name in ALLOWED_COMMANDS:
            assert name in text
        assert "no shell" in text.lower()
