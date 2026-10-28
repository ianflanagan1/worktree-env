"""worktree-env new

Creates a worktree in the lowest free slot: beside the main checkout as <main>-wt<n>, detached at
the tip of the project's base branch, or of the repository's default branch when it sets none.
Its .env file starts as a copy of the main checkout's, so it has the same secrets, with the
slot's own URL and compose project set. Then it runs the project's up command there, to start
the stack.
"""

from cli_kit import cli, proc
from cli_kit.outcome import Done, Precondition, changed
from git_default_branch import default_branch

from worktree_env import context, envfile, settings, slots
from worktree_env.context import Context


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "new",
        help="create a worktree in the lowest free slot and start its stack",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.set_defaults(run=lambda args: new(context.load()))


def new(ctx: Context) -> Done:
    project = ctx.project
    used = ctx.used()
    slot = slots.lowest_free(set(used) | {slots.MAIN}, project.slots)
    if slot is None:
        raise Precondition(
            f"All {project.slots} worktree slots are in use.",
            *(f"{s}  {w.path}" for s, w in sorted(used.items()) if s != slots.MAIN),
            "Remove one with `worktree-env rm <slot>`.",
        )
    path = slots.path_for(slot, ctx.main)
    if path.exists():
        raise Precondition(f"{path} already exists, but isn't a worktree.", "Move it away first.")
    main_env = ctx.main / project.env_file
    if not main_env.is_file():
        raise Precondition(f"No {project.env_file} in the main checkout to copy.")
    base = project.base or default_branch(ctx.main, ask_remote=True)
    if base is None:
        raise Precondition(
            "Can't tell which branch to start the worktree from.",
            "Set base in .config/ianf-worktree-env.toml, or the repository's default branch"
            " with: git config default-branch.name <branch>",
        )

    proc.output("git", "worktree", "add", "--detach", str(path), base)
    changed(f"Created {path}, detached at {base}.")

    values = settings.values(project, slot, ctx.machine.domain, path.name)
    env = path / project.env_file
    env.parent.mkdir(parents=True, exist_ok=True)
    env.write_text(envfile.apply(main_env.read_text(), values))
    changed(f"Wrote {project.env_file} for {slot}.")

    if project.up:
        context.run_in(path, project.up)
        changed(f"Ran {' '.join(project.up)}.")

    return Done(
        f"Created {slot}.",
        f"https://{slots.host(slot, project.name, ctx.machine.domain)}",
        str(path),
    )
