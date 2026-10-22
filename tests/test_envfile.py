from worktree_env.envfile import apply


def test_an_existing_variable_is_set_in_place_and_every_other_line_is_kept():
    text = "# The app\nAPP_URL=http://localhost:8080\nSECRET=abc\n"
    assert apply(text, {"APP_URL": "https://main.app.dev.example.com"}) == (
        "# The app\nAPP_URL=https://main.app.dev.example.com\nSECRET=abc\n"
    )


def test_a_missing_variable_is_added_at_the_end():
    assert apply("SECRET=abc\n", {"APP_HOST": "x"}) == (
        "SECRET=abc\n\n# Set by worktree-env\nAPP_HOST=x\n"
    )


def test_a_file_ending_without_a_newline_gets_one_before_added_variables():
    assert (
        apply("SECRET=abc", {"APP_HOST": "x"})
        == "SECRET=abc\n\n# Set by worktree-env\nAPP_HOST=x\n"
    )


def test_a_commented_out_variable_is_left_alone_and_the_variable_is_added():
    assert apply("# APP_URL=old\n", {"APP_URL": "new"}) == (
        "# APP_URL=old\n\n# Set by worktree-env\nAPP_URL=new\n"
    )


def test_a_variable_whose_name_only_starts_the_same_is_not_touched():
    assert apply("APP_URL_OLD=a\nAPP_URL=b\n", {"APP_URL": "c"}) == "APP_URL_OLD=a\nAPP_URL=c\n"


def test_every_assignment_of_a_variable_is_set():
    assert apply("A=1\nA=2\n", {"A": "3"}) == "A=3\nA=3\n"


def test_a_value_with_spaces_or_a_hash_is_quoted():
    assert apply("A=1\n", {"A": "two words"}) == 'A="two words"\n'
    assert apply("A=1\n", {"A": "x#y"}) == 'A="x#y"\n'


def test_text_already_set_comes_back_unchanged():
    text = "APP_URL=https://main.app.dev.example.com\n"
    assert apply(text, {"APP_URL": "https://main.app.dev.example.com"}) == text
