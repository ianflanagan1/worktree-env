"""Gathering what every command works from: the repository's checkouts, the project's config and
this machine's."""

import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from cli_kit import proc
from cli_kit.outcome import Failure, Precondition

from worktree_env import config, slots
from worktree_env.config import Invalid, Machine, Project
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
    return Context(main, here, _project(main), _machine(), worktrees)


def _project(main: Path) -> Project:
    path = main / ".workspace.toml"
    read = config.project(_toml(path, f"No .workspace.toml in the main checkout, {main}."))
    if isinstance(read, Invalid):
        raise Precondition(read.message, *read.details, f"In {path}.")
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
