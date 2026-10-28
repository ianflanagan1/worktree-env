"""The two configs: a project's, in its .config/ianf-worktree-env.toml, and this machine's, in the
tool's config.toml. Each is read from a parsed TOML table into a value, or an Invalid saying what's
wrong."""

import re
import string
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

PURPOSE = "worktree-env"
PLACEHOLDERS = ("slot", "host", "dir")
LABEL = r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?"


@dataclass(frozen=True)
class Invalid:
    message: str
    details: tuple[str, ...] = ()

    def __init__(self, message: str, *details: str) -> None:
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "details", details)


class Version(IntEnum):
    """The versions of ianf-worktree-env.toml's format worktree-env reads."""

    V1 = 1


@dataclass(frozen=True)
class Project:
    name: str  # the DNS label under the domain: <slot>.<name>.<domain>
    slots: int  # how many worktrees besides the main checkout
    base: str | None  # the branch a new worktree starts from; None for the default branch
    env_file: Path  # relative to the checkout
    env: dict[str, str]  # variables to set in env_file, with {slot}, {host} and {dir}
    up: tuple[str, ...]  # run in a new worktree, to start its stack
    down: tuple[str, ...]  # run before removing a worktree, to stop its stack and delete its data


@dataclass(frozen=True)
class Machine:
    domain: str  # dev names go under it, such as dev.example.com


def project(table: dict) -> Project | Invalid:
    """A project from the settings in version 1 of its file."""
    name = table.get("name")
    if not isinstance(name, str) or not re.fullmatch(LABEL, name):
        return Invalid(
            "name must be a DNS label.",
            "Lowercase letters, digits and inner hyphens, at most 63 characters.",
        )
    slots = table.get("slots", 9)
    if type(slots) is not int or not 1 <= slots <= 99:
        return Invalid("slots must be a whole number from 1 to 99.")
    base = table.get("base")
    if base is not None and (not isinstance(base, str) or not base):
        return Invalid("base must name a branch.")
    env_file = table.get("env-file")
    if not isinstance(env_file, str) or not env_file:
        return Invalid("env-file must name the checkout's .env file.")

    env = table.get("env", {})
    if not isinstance(env, dict) or not all(isinstance(v, str) for v in env.values()):
        return Invalid("env must be a table of strings.")
    for key, value in env.items():
        unknown = [
            field
            for _, field, _, _ in string.Formatter().parse(value)
            if field is not None and field not in PLACEHOLDERS
        ]
        if unknown:
            return Invalid(
                f"env.{key} uses an unknown placeholder: {{{unknown[0]}}}.",
                "Use {slot}, {host} or {dir}.",
            )

    commands = {}
    for key in ("up", "down"):
        command = table.get(key, ())
        if command != () and (
            not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) for part in command)
        ):
            return Invalid(f"{key} must be a command as a list of strings.")
        commands[key] = tuple(command)

    return Project(name, slots, base, Path(env_file), dict(env), commands["up"], commands["down"])


def machine(config: dict) -> Machine | Invalid:
    domain = config.get("domain")
    if not isinstance(domain, str) or not re.fullmatch(rf"{LABEL}(\.{LABEL})+", domain):
        return Invalid(
            "domain in config.toml must be a domain name, such as dev.example.com.",
        )
    return Machine(domain)
