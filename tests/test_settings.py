from worktree_env.config import Project
from worktree_env.settings import values

PROJECT = Project(
    name="myapp",
    slots=9,
    base="main",
    env_file=__import__("pathlib").Path("app/.env"),
    env={
        "COMPOSE_PROJECT_NAME": "{dir}",
        "APP_URL": "https://{host}",
        "SESSION_DOMAIN": "{host}",
        "SLOT": "{slot}",
        "SECURE": "true",
    },
    up=(),
    down=(),
)


def test_each_value_fills_in_the_slot_its_host_and_its_directory():
    assert values(PROJECT, "wt3", "dev.example.com", "my-app-wt3") == {
        "COMPOSE_PROJECT_NAME": "my-app-wt3",
        "APP_URL": "https://wt3.myapp.dev.example.com",
        "SESSION_DOMAIN": "wt3.myapp.dev.example.com",
        "SLOT": "wt3",
        "SECURE": "true",
    }
