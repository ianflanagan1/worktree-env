"""Gathering what every command works from: the repository's checkouts, the project's config and
this machine's."""

import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

import repo_settings
from cli_kit import proc
from cli_kit.outcome import Failure, Precondition
from repo_settings import Missing, Settings, Source, Unlocatable

from worktree_env import config, slots
from worktree_env.config import Invalid, Machine, Project, Version
from worktree_env.worktrees import Worktree, parse

# The tool's root: .venv's parent, as `uv sync` builds it there. Gitignored, as each machine has
# its own. WORKTREE_ENV_CONFIG names another file.
CONFIG = Path(os.environ.get("WORKTREE_ENV_CONFIG") or Path(sys.prefix).parent / "config.toml")


@dataclass(frozen=True)
class Context:
    main: Path  # the main checkout
    here: Path  # the checkout the command was run in
    project: Project
    machine: Machine
    worktrees: list[Worktree]

    def slot_of(self, path: Path) -> str | None:
        return slots.slot_of(path, self.main, self.project.slots)

    def used(self) -> dict[str, Worktree]:
        """Each slot in use, with its worktree."""
        return {slot: w for w in self.worktrees if (slot := self.slot_of(w.path)) is not None}


def load() -> Context:
    if not proc.succeeds("git", "rev-parse", "--show-toplevel"):
        raise Precondition("Not in a git repository.")
    here = Path(proc.output("git", "rev-parse", "--show-toplevel")).resolve()
    worktrees = parse(proc.output("git", "worktree", "list", "--porcelain"))
    main = worktrees[0].path.resolve()  # git always lists the main worktree first
    worktrees = [Worktree(w.path.resolve(), w.head, w.branch) for w in worktrees]
    return Context(main, here, _project(here), _machine(), worktrees)


def _project(here: Path) -> Project:
    """The project's settings as committed on the default branch, which every new worktree starts
    from, so every checkout goes by the same slots. Says so on stderr when this checkout's own copy
    differs, as its edits aren't used until they're committed there."""
    settings = repo_settings.read(Source.LOCAL_DEFAULT_BRANCH, here, config.PURPOSE, Version)
    match settings:
        case Settings():
            pass
        case Missing():
            raise Precondition(f"No {settings.where}.", "Add one, as worktree-env's README shows.")
        case Unlocatable() | repo_settings.Invalid():
            raise Precondition(settings.message, *settings.details)
        case _:
            assert_never(settings)
    if note := repo_settings.notice(settings):
        print(note, file=sys.stderr)
    match settings.version:
        case Version.V1:
            read = config.project(settings.table)
        case _:
            assert_never(settings.version)
    if isinstance(read, Invalid):
        raise Precondition(read.message, *read.details, f"In {settings.where}.")
    return read


def _machine() -> Machine:
    read = config.machine(
        _toml(CONFIG, f"No {CONFIG}.", "Copy config.example.toml there and set your domain.")
    )
    if isinstance(read, Invalid):
        raise Precondition(read.message, f"In {CONFIG}.")
    return read


def _toml(path: Path, missing: str, *details: str) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except FileNotFoundError:
        raise Precondition(missing, *details) from None
    except tomllib.TOMLDecodeError as error:
        raise Precondition(f"{path} isn't valid TOML.", str(error)) from None


def run_in(directory: Path, command: tuple[str, ...]) -> None:
    """Runs a project's command in a checkout, with its output shown. Raises Failure when it
    exits non-zero."""
    if subprocess.run(command, cwd=directory, check=False).returncode != 0:
        raise Failure(f"{' '.join(command)} failed in {directory}.")
