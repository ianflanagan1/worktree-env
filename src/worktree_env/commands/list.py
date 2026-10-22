"""worktree-env list

Lists the project's slots in use, with each one's URL, directory and what it has checked out,
then any worktrees outside the pool.
"""

from cli_kit import cli
from cli_kit.outcome import NothingToDo

from worktree_env import context, slots
from worktree_env.context import Context
from worktree_env.worktrees import Worktree


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "list",
        help="list the slots in use",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.set_defaults(run=lambda args: list_slots(context.load()))


def list_slots(ctx: Context) -> NothingToDo:
    used = ctx.used()
    order = [slots.MAIN, *(slots.numbered(n) for n in range(1, ctx.project.slots + 1))]
    rows = [
        (slot, f"https://{slots.host(slot, ctx.project.name, ctx.machine.domain)}", used[slot])
        for slot in order
        if slot in used
    ]
    url_width = max(len(url) for _, url, _ in rows)
    for slot, url, worktree in rows:
        print(f"{slot:<5} {url:<{url_width}}  {worktree.path}  {_checked_out(worktree)}")
    outside = [w for w in ctx.worktrees if ctx.slot_of(w.path) is None]
    if outside:
        print("\nOutside the pool:")
        for worktree in outside:
            print(f"      {worktree.path}  {_checked_out(worktree)}")
    print()
    return NothingToDo(f"{len(used) - 1} of {ctx.project.slots} worktree slots in use.")


def _checked_out(worktree: Worktree) -> str:
    return worktree.branch or f"detached at {worktree.head[:7]}"
