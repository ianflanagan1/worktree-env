"""What a checkout's .env file is set to for its slot."""

from worktree_env.config import Project
from worktree_env.slots import host


def values(project: Project, slot: str, domain: str, directory: str) -> dict[str, str]:
    fields = {"slot": slot, "host": host(slot, project.name, domain), "dir": directory}
    return {key: value.format_map(fields) for key, value in project.env.items()}
