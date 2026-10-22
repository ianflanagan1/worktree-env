"""Reading `git worktree list --porcelain`."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Worktree:
    path: Path
    head: str
    branch: str | None  # None when detached


def parse(porcelain: str) -> list[Worktree]:
    worktrees = []
    for block in porcelain.strip().split("\n\n"):
        fields = dict(
            line.split(" ", 1) if " " in line else (line, "") for line in block.splitlines()
        )
        if "worktree" not in fields:
            continue
        branch = fields.get("branch")
        worktrees.append(
            Worktree(
                Path(fields["worktree"]),
                fields.get("HEAD", ""),
                branch.removeprefix("refs/heads/") if branch else None,
            )
        )
    return worktrees
