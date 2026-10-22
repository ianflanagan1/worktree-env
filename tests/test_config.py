from pathlib import Path

from worktree_env.config import Invalid, Machine, Project, machine, project

PROJECT = {
    "worktree-env": {
        "name": "myapp",
        "env-file": "app/.env",
        "up": ["task", "setup"],
        "down": ["task", "down:delete"],
        "env": {"APP_URL": "https://{host}", "COMPOSE_PROJECT_NAME": "{dir}"},
    }
}


def test_a_project_is_read_from_its_worktree_env_table():
    assert project(PROJECT) == Project(
        name="myapp",
        slots=9,
        base="main",
        env_file=Path("app/.env"),
        env={"APP_URL": "https://{host}", "COMPOSE_PROJECT_NAME": "{dir}"},
        up=("task", "setup"),
        down=("task", "down:delete"),
    )


def test_a_project_may_leave_out_its_up_and_down_commands_and_set_its_slots_and_base():
    table = {"name": "myapp", "env-file": ".env", "slots": 3, "base": "trunk", "env": {}}
    read = project({"worktree-env": table})
    assert isinstance(read, Project)
    assert (read.slots, read.base, read.up, read.down) == (3, "trunk", (), ())


def test_a_workspace_without_the_table_is_invalid():
    assert project({"tracker": {}}) == Invalid(
        "No [worktree-env] table in .workspace.toml.",
    )


def test_a_project_name_must_be_a_dns_label():
    for name in ("My App", "my_app", "-app", "app-", "", "a" * 64):
        read = project({"worktree-env": PROJECT["worktree-env"] | {"name": name}})
        assert isinstance(read, Invalid), name


def test_a_project_must_name_its_env_file():
    table = dict(PROJECT["worktree-env"])
    del table["env-file"]
    assert isinstance(project({"worktree-env": table}), Invalid)


def test_slots_must_be_between_1_and_99():
    for slots in (0, 100, "9", True):
        read = project({"worktree-env": PROJECT["worktree-env"] | {"slots": slots}})
        assert isinstance(read, Invalid), slots


def test_an_env_value_may_only_use_known_placeholders():
    table = PROJECT["worktree-env"] | {"env": {"A": "{hots}"}}
    assert project({"worktree-env": table}) == Invalid(
        "env.A in [worktree-env] uses an unknown placeholder: {hots}.",
        "Use {slot}, {host} or {dir}.",
    )


def test_commands_must_be_lists_of_strings():
    for up in ("task setup", [1], []):
        read = project({"worktree-env": PROJECT["worktree-env"] | {"up": up}})
        assert isinstance(read, Invalid), up


def test_the_machine_config_names_the_domain_dev_names_go_under():
    assert machine({"domain": "dev.example.com"}) == Machine(domain="dev.example.com")


def test_a_machine_config_without_a_valid_domain_is_invalid():
    for config in ({}, {"domain": ""}, {"domain": "dev.example.com."}, {"domain": "a b.com"}):
        assert isinstance(machine(config), Invalid), config
