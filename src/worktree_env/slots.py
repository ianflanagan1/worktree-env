"""Slots: the fixed pool of names a project's checkouts are served under.

The main checkout is slot `main`. Other worktrees are `wt1` to `wt<slots>`, each in a directory
beside the main checkout named after it: `my-app` has `my-app-wt1`, `my-app-wt2` and so on. A
slot's host is `<slot>.<project>.<domain>`, registered in advance wherever a service needs exact
URLs, such as OAuth redirects.
"""

import re
from pathlib import Path

MAIN = "main"


def numbered(n: int) -> str:
    return f"wt{n}"


def slot_of(path: Path, main: Path, slots: int) -> str | None:
    """The slot of the checkout at path, or None if it's outside the pool."""
    if path == main:
        return MAIN
    if path.parent != main.parent:
        return None
    match = re.fullmatch(re.escape(main.name) + r"-wt([1-9][0-9]*)", path.name)
    if match is None or int(match[1]) > slots:
        return None
    return numbered(int(match[1]))


def path_for(slot: str, main: Path) -> Path:
    return main if slot == MAIN else main.parent / f"{main.name}-{slot}"


def lowest_free(used: set[str], slots: int) -> str | None:
    """The slot a new worktree takes, or None when all are in use."""
    return next((numbered(n) for n in range(1, slots + 1) if numbered(n) not in used), None)


def host(slot: str, project: str, domain: str) -> str:
    return f"{slot}.{project}.{domain}"
