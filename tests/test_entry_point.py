"""The worktree-env command that uv installs into .venv/bin, run against a throwaway repository."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BIN = Path(sys.prefix) / "bin" / "worktree-env"

SETTINGS = """\
version = 1
name = "myapp"
slots = 2
env-file = "app/.env"
up = ["sh", "-c", "echo started > up.txt"]
down = ["sh", "-c", "echo stopped"]

[env]
COMPOSE_PROJECT_NAME = "{dir}"
APP_URL = "https://{host}"
"""


@pytest.fixture
def main(tmp_path: Path) -> Path:
    """A main checkout, my-app, with a project config and a gitignored .env holding a secret."""
    repo = tmp_path / "my-app"
    (repo / "app").mkdir(parents=True)
    (repo / ".config").mkdir()
    (repo / ".config" / "ianf-worktree-env.toml").write_text(SETTINGS)
    (repo / ".gitignore").write_text("app/.env\nup.txt\n")
    (repo / "app" / ".env").write_text("SECRET=abc\nAPP_URL=http://localhost:8080\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "Start")
    return repo


@pytest.fixture(autouse=True)
def no_global_git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Git reads none of this machine's config, such as its init.defaultBranch."""
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture(autouse=True)
def machine_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "config.toml"
    config.write_text('domain = "dev.example.com"\n')
    monkeypatch.setenv("WORKTREE_ENV_CONFIG", str(config))


def git(repo: Path, *args: str) -> str:
    env = os.environ | {
        "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.com",
    }  # fmt: skip
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    ).stdout


def launch(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    # A new session has no controlling terminal, as when an agent runs the command.
    return subprocess.run(
        [BIN, *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=os.environ | {"NO_COLOR": "1"},
        start_new_session=True,
    )


def test_help_lists_the_commands(main: Path):
    result = launch("--help", cwd=main)
    assert result.returncode == 0
    for command in ("list", "new", "rm", "configure"):
        assert f"  {command}" in result.stdout


def test_a_project_without_its_settings_file_on_the_default_branch_is_named(main: Path):
    git(main, "rm", "-q", ".config/ianf-worktree-env.toml")
    git(main, "commit", "-q", "-m", "Drop the settings")
    result = launch("configure", cwd=main)
    assert result.returncode == 1
    assert result.stderr.startswith("⚠️ No .config/ianf-worktree-env.toml on main.\n")


def test_settings_are_read_as_committed_on_the_default_branch(main: Path):
    git(main, "switch", "-q", "-c", "spike")
    settings = main / ".config" / "ianf-worktree-env.toml"
    settings.write_text(SETTINGS.replace("myapp", "spike"))
    git(main, "commit", "-q", "-am", "Rename on a branch")
    result = launch("configure", cwd=main)
    assert result.returncode == 0, result.stderr
    assert "APP_URL=https://main.myapp.dev.example.com" in (main / "app" / ".env").read_text()


def test_edits_to_a_checkouts_own_copy_are_said_to_be_unused(main: Path):
    settings = main / ".config" / "ianf-worktree-env.toml"
    settings.write_text(SETTINGS.replace("myapp", "edited"))
    result = launch("configure", cwd=main)
    assert result.returncode == 0, result.stderr
    assert result.stderr.startswith(
        f"Your edits to {settings.resolve()} aren't used: .config/ianf-worktree-env.toml on main"
        " is.\n"
    )
    assert "APP_URL=https://main.myapp.dev.example.com" in (main / "app" / ".env").read_text()


def test_configure_sets_the_main_checkouts_env_for_the_main_slot(main: Path):
    result = launch("configure", cwd=main)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(
        "✅ Set app/.env for main.\nhttps://main.myapp.dev.example.com\n"
    )
    assert (main / "app" / ".env").read_text() == (
        "SECRET=abc\nAPP_URL=https://main.myapp.dev.example.com\n"
        "\n# Set by worktree-env\nCOMPOSE_PROJECT_NAME=my-app\n"
    )
    assert launch("configure", cwd=main).stdout == "➖ app/.env is already set for main.\n"


def test_new_creates_a_worktree_in_the_lowest_free_slot_with_the_main_checkouts_secrets(main: Path):
    result = launch("new", cwd=main)
    assert result.returncode == 0, result.stderr
    wt1 = main.parent / "my-app-wt1"
    assert result.stdout.splitlines()[-3:] == [
        "✅ Created wt1.",
        "https://wt1.myapp.dev.example.com",
        str(wt1.resolve()),
    ]
    assert (wt1 / "app" / ".env").read_text() == (
        "SECRET=abc\nAPP_URL=https://wt1.myapp.dev.example.com\n"
        "\n# Set by worktree-env\nCOMPOSE_PROJECT_NAME=my-app-wt1\n"
    )
    assert (wt1 / "up.txt").read_text() == "started\n"
    assert git(wt1, "branch", "--show-current") == ""


def test_new_starts_from_the_repositorys_default_branch_when_no_base_is_set(main: Path):
    git(main, "branch", "-m", "main", "trunk")
    git(main, "config", "default-branch.name", "trunk")
    git(main, "commit", "-q", "--allow-empty", "-m", "On trunk")
    git(main, "checkout", "-q", "-b", "spike")
    git(main, "commit", "-q", "--allow-empty", "-m", "On spike")
    result = launch("new", cwd=main)
    assert result.returncode == 0, result.stderr
    assert "detached at trunk." in result.stdout
    wt1 = main.parent / "my-app-wt1"
    assert git(wt1, "log", "-1", "--format=%s").strip() == "On trunk"


def test_new_stops_before_changing_anything_when_it_cannot_tell_where_to_start(main: Path):
    git(main, "branch", "master")
    result = launch("new", cwd=main)
    assert result.returncode == 1
    assert result.stderr.startswith("⚠️ Can't tell the default branch: there's no remote")
    assert not (main.parent / "my-app-wt1").exists()


def test_list_shows_each_slot_in_use(main: Path):
    launch("new", cwd=main)
    result = launch("list", cwd=main)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0].split()[:3] == [
        "main",
        "https://main.myapp.dev.example.com",
        str(main.resolve()),
    ]
    assert lines[1].split()[:2] == ["wt1", "https://wt1.myapp.dev.example.com"]
    assert lines[-1] == "➖ 1 of 2 worktree slots in use."


def test_new_stops_when_every_slot_is_in_use(main: Path):
    launch("new", cwd=main)
    launch("new", cwd=main)
    result = launch("new", cwd=main)
    assert result.returncode == 1
    assert result.stderr.startswith("⚠️ All 2 worktree slots are in use.\n")


def test_removing_a_free_slot_has_nothing_to_do(main: Path):
    result = launch("rm", "wt1", cwd=main)
    assert (result.returncode, result.stdout) == (0, "➖ wt1 isn't in use.\n")


def test_removing_a_worktree_needs_its_name_typed_at_a_terminal(main: Path):
    launch("new", cwd=main)
    result = launch("rm", "wt1", cwd=main)
    assert result.returncode == 1
    assert result.stderr.startswith("⚠️ No terminal to confirm at.")
    assert (main.parent / "my-app-wt1").is_dir()


def test_a_worktree_with_uncommitted_changes_is_not_removed(main: Path):
    launch("new", cwd=main)
    (main.parent / "my-app-wt1" / "draft.txt").write_text("unsaved")
    result = launch("rm", "wt1", cwd=main)
    assert result.returncode == 1
    assert result.stderr.startswith("⚠️ wt1 has uncommitted changes.\n?? draft.txt")


def test_a_worktree_with_commits_on_no_branch_is_not_removed(main: Path):
    launch("new", cwd=main)
    wt1 = main.parent / "my-app-wt1"
    git(wt1, "commit", "-q", "--allow-empty", "-m", "Work in progress")
    result = launch("rm", "wt1", cwd=main)
    assert result.returncode == 1
    assert result.stderr.startswith("⚠️ wt1 has commits on no branch, which removing it would lose.")


def test_the_main_checkout_cannot_be_removed(main: Path):
    result = launch("rm", "main", cwd=main)
    assert (result.returncode, result.stderr) == (1, "⚠️ The main checkout can't be removed.\n")


def test_a_checkout_outside_the_pool_is_not_configured(main: Path):
    elsewhere = main.parent / "elsewhere"
    git(main, "worktree", "add", "-q", "--detach", str(elsewhere))
    result = launch("configure", cwd=elsewhere)
    assert result.returncode == 1
    assert result.stderr.startswith(f"⚠️ {elsewhere.resolve()} isn't in a slot.")


def test_without_the_machine_config_it_says_how_to_create_it(main: Path, tmp_path: Path):
    (tmp_path / "config.toml").unlink()
    result = launch("list", cwd=main)
    assert result.returncode == 1
    assert "Copy config.example.toml there and set your domain." in result.stderr
