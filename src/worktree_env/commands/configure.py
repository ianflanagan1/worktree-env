"""worktree-env configure

Sets the variables in this checkout's .env file for its slot: its URL, its compose project and
whatever else the project's .config/ianf-worktree-env.toml lists. Every other line is kept. Run it
once in the main checkout; `worktree-env new` runs it for each new worktree.
"""

from cli_kit import cli
from cli_kit.outcome import Done, NothingToDo, Precondition

from worktree_env import context, envfile, settings, slots
from worktree_env.context import Context


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "configure",
        help="set this checkout's .env for its slot",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.set_defaults(run=lambda args: configure(context.load()))


def configure(ctx: Context) -> Done | NothingToDo:
    slot = ctx.slot_of(ctx.here)
    if slot is None:
        raise Precondition(
            f"{ctx.here} isn't in a slot.",
            f"Slots are the main checkout and its siblings {ctx.main.name}-wt1 to"
            f" {ctx.main.name}-wt{ctx.project.slots}.",
        )
    path = ctx.here / ctx.project.env_file
    if not path.is_file():
        raise Precondition(f"No {ctx.project.env_file} in {ctx.here}.", "Create it first.")
    text = path.read_text()
    values = settings.values(ctx.project, slot, ctx.machine.domain, ctx.here.name)
    updated = envfile.apply(text, values)
    if updated == text:
        return NothingToDo(f"{ctx.project.env_file} is already set for {slot}.")
    path.write_text(updated)
    return Done(
        f"Set {ctx.project.env_file} for {slot}.",
        f"https://{slots.host(slot, ctx.project.name, ctx.machine.domain)}",
        "Restart its stack for it to take effect.",
    )
