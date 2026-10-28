# worktree-env

`worktree-env` gives each git worktree of a project its own slot: a fixed HTTPS hostname, a `.env` file set for it, and its own Docker Compose stack. It creates worktrees in free slots and removes them, so you can run several copies of a project side by side, each on an origin shaped like production's.

```
$ worktree-env new
Created /home/me/projects/my-app-wt1, detached at main.
Wrote app/.env for wt1.
...
✅ Created wt1.
https://wt1.myapp.dev.example.com
/home/me/projects/my-app-wt1

$ worktree-env
main  https://main.myapp.dev.example.com  /home/me/projects/my-app      main
wt1   https://wt1.myapp.dev.example.com   /home/me/projects/my-app-wt1  detached at 3f2a1c9

➖ 1 of 9 worktree slots in use.
```

Runs on macOS and Linux. Built on [cli-kit](https://github.com/ianflanagan1/cli-kit), so its help and status lines work like those of my other command line tools. It pairs with [local-https-proxy](https://github.com/ianflanagan1/local-https-proxy), which serves each slot's hostname with a real certificate.

## Why a fixed pool of slots

The main checkout is slot `main`; other worktrees take `wt1` to `wt9`. Slots are numbered rather than named after the work, because services that redirect back to your app, such as Google's and Discord's OAuth, accept only exact URLs registered in advance. A fixed pool can be registered once, and every worktree's login then works just as production's does.

## Commands

`worktree-env help` lists them, and `worktree-env help <command>` shows one in full.

| Command | Does |
|---|---|
| `worktree-env` or `worktree-env list` | Lists the slots in use, with each one's URL, directory and what it has checked out |
| `worktree-env new` | Creates a worktree in the lowest free slot, beside the main checkout as `<main>-wt<n>` and detached at the tip of the base branch, or of the default branch (see [git-default-branch](../git-default-branch)). Copies the main checkout's `.env`, so it has the same secrets, sets the slot's variables in it, and runs the project's `up` command |
| `worktree-env rm <slot>` | Runs the project's `down` command in that worktree, then removes it, freeing the slot. Refuses one with uncommitted changes or commits on no branch, and asks you to type the slot's name |
| `worktree-env configure` | Sets this checkout's `.env` for its slot. Run it once in the main checkout |

## Configuring a project

A project declares its slots in `.config/ianf-worktree-env.toml`, committed in its repository, as [repo-settings](../repo-settings) describes. worktree-env reads the copy committed on the default branch, which every new worktree starts from, so every checkout goes by the same slots. An edit takes effect once it's committed there; until then, worktree-env says on stderr that your checkout's copy isn't used:

```toml
#:schema https://raw.githubusercontent.com/ianflanagan1/worktree-env/main/schema/ianf-worktree-env.v1.json
version = 1                       # the version of this file's format: see schema/
name = "myapp"                    # the DNS label: <slot>.myapp.<domain>
slots = 9                         # worktrees besides the main checkout (default 9)
base = "main"                     # the branch new worktrees start from (default: the repository's default branch)
env-file = "app/.env"             # the checkout's .env, gitignored
up = ["task", "setup"]            # run in a new worktree, to start its stack (optional)
down = ["task", "down:delete"]    # run before removing one, to stop its stack and delete its data (optional)

[env]                             # set in env-file; {slot}, {host} and {dir} are filled in
COMPOSE_PROJECT_NAME = "{dir}"
COMPOSE_FILE = "compose.yaml:compose.local-https-proxy.yaml"
APP_URL = "https://{host}"
```

`{slot}` is `main` or `wt<n>`, `{host}` is `<slot>.<name>.<domain>`, and `{dir}` is the checkout directory's name. Every other line of the `.env` file is kept as it is.

Give each slot's compose project its own name, as `COMPOSE_PROJECT_NAME = "{dir}"` does, so stacks don't share containers or volumes, and publish no fixed host ports, so they don't collide.

## Setup

```sh
cd ~/projects/cli/worktree-env
devbox run setup   # uv sync, creates config.toml, then links worktree-env into ~/.local/bin
```

Then set `domain` in `config.toml`: the domain every project's dev names go under, such as `dev.example.com`.

## Development

```sh
devbox run test    # pytest
devbox run lint    # ruff check and format
```

## License

MIT
