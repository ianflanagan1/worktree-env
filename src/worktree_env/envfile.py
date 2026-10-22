"""Setting variables in a .env file, keeping everything else in it as it was."""

import re


def apply(text: str, values: dict[str, str]) -> str:
    """text with each variable in values set: in place where it's assigned, otherwise added at
    the end. Comments, other variables and the order of lines are kept."""
    lines = text.splitlines()
    missing = dict(values)
    for i, line in enumerate(lines):
        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)=", line)
        if match and match[1] in values:
            lines[i] = _assignment(match[1], values[match[1]])
            missing.pop(match[1], None)
    if missing:
        lines += ["", "# Set by worktree-env", *(_assignment(k, v) for k, v in missing.items())]
    return "\n".join(lines) + "\n" if lines else ""


def _assignment(name: str, value: str) -> str:
    if re.search(r"[\s#\"'$\\]", value):
        value = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return f"{name}={value}"
