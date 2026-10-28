import json
import re
import tomllib
from pathlib import Path

import jsonschema

from worktree_env.config import Invalid, Machine, Project, machine, project

ROOT = Path(__file__).parent.parent
SCHEMA = ROOT / "schema" / "ianf-worktree-env.v1.json"
PROJECT = {
    "name": "myapp",
    "env-file": "app/.env",
    "up": ["task", "setup"],
    "down": ["task", "down:delete"],
    "env": {"APP_URL": "https://{host}", "COMPOSE_PROJECT_NAME": "{dir}"},
}


def test_a_project_is_read_from_its_settings():
    assert project(PROJECT) == Project(
        name="myapp",
        slots=9,
        base=None,
        env_file=Path("app/.env"),
        env={"APP_URL": "https://{host}", "COMPOSE_PROJECT_NAME": "{dir}"},
        up=("task", "setup"),
        down=("task", "down:delete"),
    )


def test_a_project_may_leave_out_its_up_and_down_commands_and_set_its_slots_and_base():
    table = {"name": "myapp", "env-file": ".env", "slots": 3, "base": "trunk", "env": {}}
    read = project(table)
    assert isinstance(read, Project)
    assert (read.slots, read.base, read.up, read.down) == (3, "trunk", (), ())


def test_a_project_name_must_be_a_dns_label():
    for name in ("My App", "my_app", "-app", "app-", "", "a" * 64):
        read = project(PROJECT | {"name": name})
        assert isinstance(read, Invalid), name


def test_a_project_must_name_its_env_file():
    table = dict(PROJECT)
    del table["env-file"]
    assert isinstance(project(table), Invalid)


def test_slots_must_be_between_1_and_99():
    for slots in (0, 100, "9", True):
        read = project(PROJECT | {"slots": slots})
        assert isinstance(read, Invalid), slots


def test_an_env_value_may_only_use_known_placeholders():
    table = PROJECT | {"env": {"A": "{hots}"}}
    assert project(table) == Invalid(
        "env.A uses an unknown placeholder: {hots}.",
        "Use {slot}, {host} or {dir}.",
    )


def test_commands_must_be_lists_of_strings():
    for up in ("task setup", [1], []):
        read = project(PROJECT | {"up": up})
        assert isinstance(read, Invalid), up


def test_the_machine_config_names_the_domain_dev_names_go_under():
    assert machine({"domain": "dev.example.com"}) == Machine(domain="dev.example.com")


def test_a_machine_config_without_a_valid_domain_is_invalid():
    for config in ({}, {"domain": ""}, {"domain": "dev.example.com."}, {"domain": "a b.com"}):
        assert isinstance(machine(config), Invalid), config


def test_the_readme_s_example_names_the_schema_and_meets_it():
    readme = (ROOT / "README.md").read_text()
    example = re.search(r"```toml\n(#:schema .*?)```", readme, re.DOTALL)
    assert example
    schema = json.loads(SCHEMA.read_text())
    assert example[1].splitlines()[0] == f"#:schema {schema['$id']}"
    jsonschema.validate(tomllib.loads(example[1]), schema)


def test_the_readme_s_example_is_a_project():
    readme = (ROOT / "README.md").read_text()
    example = re.search(r"```toml\n(#:schema .*?)```", readme, re.DOTALL)
    assert example
    settings = tomllib.loads(example[1])
    del settings["version"]
    assert isinstance(project(settings), Project)
