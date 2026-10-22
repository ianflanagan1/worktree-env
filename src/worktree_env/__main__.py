"""`worktree-env <command> ...`: each git worktree of a project in its own slot, with its own
HTTPS hostname and stack. With no command, `worktree-env list`."""

import sys

from cli_kit import cli

from worktree_env.commands import configure, new, rm
from worktree_env.commands import list as list_command

COMMANDS = [list_command, new, rm, configure]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    return cli.run(
        "worktree-env",
        "Gives each git worktree of a project its own slot: an HTTPS hostname, a .env file and a"
        " stack.",
        COMMANDS,
        argv or ["list"],
    )


if __name__ == "__main__":
    sys.exit(main())
