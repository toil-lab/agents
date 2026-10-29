"""Shared helpers for the toil-lab guard hooks (Claude Code PreToolUse hooks).

Each guard reads the hook input from stdin and either prints nothing (no opinion) or prints one
permission decision. Guards fail open: an internal error goes to stderr with exit code 1, which
Claude Code reports to the user before letting the tool call proceed.

The guards catch mistakes before they happen. They are not a security boundary: RBAC on the
cluster contexts, CODEOWNERS, and branch protection are.
"""
import json, os, re, shlex, sys

CONFIG_NAME = "toil.json"
SEGMENT_SPLIT = re.compile(r"\|\||&&|\||;|\n")
# Words that can sit in front of a command without being the command.
PREFIX_WORDS = {"sudo", "exec", "time", "nohup", "command", "--", "&", "env", "watch", "xargs"}
# Commands that run another command given as later arguments.
LAUNCHERS = {"wsl", "ssh", "sudo", "env", "nohup", "time", "watch", "xargs"}
# Flags that take a separate value, across kubectl, helm, docker, gcloud, and terraform.
VALUE_FLAGS = {
    "-n", "--namespace", "--context", "--kube-context", "--kubeconfig", "-l", "--selector", "-o",
    "--output", "-c", "--container", "--cluster", "--user", "-f", "--filename", "-s", "--server",
    "--field-selector", "--sort-by", "--since", "--tail", "-L", "--label-columns", "--as",
    "--as-group", "--token", "--request-timeout", "--values", "--set", "--set-string", "--version",
    "--repo", "--timeout", "-t", "--tag", "--build-arg", "-p", "--publish", "-v", "--volume", "-e",
    "--env", "--name", "--network", "--platform", "--file", "--project", "--zone", "--region",
    "-d", "--distribution", "--chdir", "-var", "-var-file", "-target",
}


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        sys.exit(0)


def decide(decision, reason):
    """Print a PreToolUse permission decision ('allow', 'ask' or 'deny') and exit."""
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def role_arg(default=None):
    """The value after --role on the hook's command line."""
    if "--role" in sys.argv:
        i = sys.argv.index("--role")
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def shell_command(data):
    """The command text of a Bash or PowerShell tool call, else None."""
    if data.get("tool_name") in ("Bash", "PowerShell"):
        return (data.get("tool_input") or {}).get("command") or ""
    return None


def segments(command):
    return [s.strip() for s in SEGMENT_SPLIT.split(command) if s.strip()]


def tokens(segment):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def command_name(token):
    """'C:\\tools\\kubectl.exe' -> 'kubectl', '$(gcloud' -> 'gcloud'."""
    base = re.split(r"[\\/]", token.lstrip("$(`"))[-1].lower()
    for ext in (".exe", ".cmd", ".ps1", ".bat"):
        if base.endswith(ext):
            return base[: -len(ext)]
    return base


def invocations(command, names, _depth=0):
    """Yield (name, args) for each call of a command in `names`, including calls nested in quoted
    strings such as `bash -c "..."` or `wsl -- sh -c '...'`."""
    for seg in segments(command):
        toks = tokens(seg)
        launched = bool(toks) and command_name(toks[0]) in LAUNCHERS
        for i, t in enumerate(toks):
            prev = toks[i - 1] if i else ""
            in_command_position = i == 0 or prev in PREFIX_WORDS or re.match(r"^\w+=", prev) or launched
            if command_name(t) in names and in_command_position:
                yield command_name(t), toks[i + 1:]
                break
            if _depth < 3 and re.search(r"\s", t):
                yield from invocations(t, names, _depth + 1)


def flag_value(args, names):
    """Value of the first flag in `names`, written as `--flag value` or `--flag=value`."""
    for i, a in enumerate(args):
        for n in names:
            if a == n and i + 1 < len(args):
                return args[i + 1]
            if a.startswith(n + "="):
                return a.split("=", 1)[1]
    return None


def positionals(args):
    """Arguments that are not flags or flag values, in order."""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a.startswith("-"):
            if "=" not in a and a in VALUE_FLAGS:
                skip = True
            continue
        out.append(a)
    return out


def normalize_path(path, cwd):
    """Absolute OS path for `path`; Git Bash style /d/x becomes D:/x on Windows."""
    if os.name == "nt":
        m = re.match(r"^/([a-zA-Z])(/.*)?$", path)
        if m:
            path = m.group(1).upper() + ":" + (m.group(2) or "/")
    if not os.path.isabs(path):
        path = os.path.join(cwd, path)
    return os.path.abspath(path)


def find_repo(path):
    """(repo_root, config) for the nearest toil.json at or above `path`, stopping at a git root.
    (None, None) when there is none."""
    d = path if os.path.isdir(path) else os.path.dirname(path)
    while True:
        cfg = os.path.join(d, CONFIG_NAME)
        if os.path.isfile(cfg):
            with open(cfg, encoding="utf-8") as f:
                return d, json.load(f)
        if os.path.isdir(os.path.join(d, ".git")):
            return None, None
        parent = os.path.dirname(d)
        if parent == d:
            return None, None
        d = parent


def run(main):
    """Run a guard's main(), turning unexpected errors into a visible, non-blocking failure."""
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"{os.path.basename(sys.argv[0])} failed and did not check this call: {e!r}\n")
        sys.exit(1)
