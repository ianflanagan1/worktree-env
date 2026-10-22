from pathlib import Path

from worktree_env.slots import MAIN, host, lowest_free, path_for, slot_of

PROJECTS = Path("/home/me/projects")
MAIN_CHECKOUT = PROJECTS / "my-app"


def test_the_main_checkout_is_the_main_slot():
    assert slot_of(MAIN_CHECKOUT, MAIN_CHECKOUT, 9) == MAIN


def test_a_sibling_named_after_the_main_checkout_with_a_slot_number_is_that_slot():
    assert slot_of(PROJECTS / "my-app-wt1", MAIN_CHECKOUT, 9) == "wt1"
    assert slot_of(PROJECTS / "my-app-wt9", MAIN_CHECKOUT, 9) == "wt9"


def test_a_worktree_anywhere_else_or_numbered_outside_the_pool_has_no_slot():
    for path in (
        PROJECTS / "elsewhere",
        PROJECTS / "my-app-wt0",
        PROJECTS / "my-app-wt10",
        PROJECTS / "my-app-wt01",
        PROJECTS / "my-app-wt",
        PROJECTS / "nested" / "my-app-wt1",
        PROJECTS / "other-app-wt1",
    ):
        assert slot_of(path, MAIN_CHECKOUT, 9) is None, path


def test_a_slot_lives_beside_the_main_checkout():
    assert path_for("wt3", MAIN_CHECKOUT) == PROJECTS / "my-app-wt3"
    assert path_for(MAIN, MAIN_CHECKOUT) == MAIN_CHECKOUT


def test_the_lowest_unused_slot_is_taken_next():
    assert lowest_free({MAIN}, 9) == "wt1"
    assert lowest_free({MAIN, "wt1", "wt2", "wt4"}, 9) == "wt3"
    assert lowest_free(set(), 9) == "wt1"


def test_there_is_no_free_slot_when_every_one_is_in_use():
    assert lowest_free({MAIN, "wt1", "wt2"}, 2) is None


def test_a_slots_host_is_the_slot_under_the_project_under_the_domain():
    assert host("wt3", "myapp", "dev.example.com") == "wt3.myapp.dev.example.com"
    assert host(MAIN, "myapp", "dev.example.com") == "main.myapp.dev.example.com"
