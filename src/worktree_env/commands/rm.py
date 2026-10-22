"""worktree-env rm <slot>

Removes the worktree in a slot, such as wt3, freeing the slot: runs the project's down command
there, which stops its stack and deletes its data, then removes the worktree. It won't remove one
with uncommitted changes or commits on no branch, which removing it would lose, and asks you to
type the slot's name first.
"""

from cli_kit import cli, proc
from cli_kit.outcome import Done, NothingToDo, Precondition, changed
from cli_kit.terminal import ask

from worktree_env import context, slots
from worktree_env.context import Context


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "rm",
        help="stop a worktree's stack, delete its data and remove it",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.add_argument("slot", help="the slot to free, such as wt3")
    parser.set_defaults(run=lambda args: rm(context.load(), args.slot))


def rm(ctx: Context, slot: str) -> Done | NothingToDo:
    if slot == slots.MAIN:
        raise Precondition("The main checkout can't be removed.")
    if slot not in {slots.numbered(n) for n in range(1, ctx.project.slots + 1)}:
        raise Precondition(f"{slot} isn't a slot.", f"Slots are wt1 to wt{ctx.project.slots}.")
    worktree = ctx.used().get(slot)
    if worktree is None:
        return NothingToDo(f"{slot} isn't in use.")
    path = str(worktree.path)

    if changes := proc.output("git", "-C", path, "status", "--porcelain"):
        raise Precondition(f"{slot} has uncommitted changes.", *changes.splitlines())
    if unreachable := proc.output(
        "git", "-C", path, "log", "--oneline", "HEAD", "--not", "--branches", "--remotes"
    ):
        raise Precondition(
            f"{slot} has commits on no branch, which removing it would lose.",
            *unreachable.splitlines(),
        )
    if ask(f"This stops {slot}'s stack and deletes its data. Type {slot} to remove it: ") != slot:
        raise Precondition("Not confirmed, so nothing was removed.")

    if ctx.project.down:
        context.run_in(worktree.path, ctx.project.down)
        changed(f"Ran {' '.join(ctx.project.down)}.")
    proc.output("git", "worktree", "remove", path)
    changed(f"Removed {path}.")
    return Done(f"Freed {slot}.")
