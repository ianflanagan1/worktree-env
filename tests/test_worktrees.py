from pathlib import Path

from worktree_env.worktrees import Worktree, parse

PORCELAIN = """\
worktree /home/me/projects/my-app
HEAD 1111111111111111111111111111111111111111
branch refs/heads/main

worktree /home/me/projects/my-app-wt1
HEAD 2222222222222222222222222222222222222222
detached

worktree /home/me/projects/my-app-wt2
HEAD 3333333333333333333333333333333333333333
branch refs/heads/try-something
locked

"""


def test_each_worktree_is_read_with_its_path_commit_and_branch():
    assert parse(PORCELAIN) == [
        Worktree(
            Path("/home/me/projects/my-app"), "1111111111111111111111111111111111111111", "main"
        ),
        Worktree(
            Path("/home/me/projects/my-app-wt1"), "2222222222222222222222222222222222222222", None
        ),
        Worktree(
            Path("/home/me/projects/my-app-wt2"),
            "3333333333333333333333333333333333333333",
            "try-something",
        ),
    ]


def test_no_output_is_no_worktrees():
    assert parse("") == []
