"""PreToolUse guard: agents act on GitHub as their own GitHub App, never as the human.

Usage in hooks.json: identity_guard.py --role dev|ops

A plain `gh` call uses the human's login, which can approve and merge PRs, so it is refused in
favor of `toil-gh`. Plain git commands that write a commit or reach a remote with credentials
are refused in favor of `toil-git`, which commits as the App's bot account and pushes with the
App's token. Read-only git commands (status, diff, log, fetch, clone of public repos) pass.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guardlib as g

# git subcommands that record an author or committer, or push with credentials.
GIT_IDENTITY = {"commit", "push", "merge", "pull", "rebase", "cherry-pick", "revert", "am"}
# git's own options that take a separate value, before the subcommand.
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def git_verb(args):
    skip = False
    for a in args:
        if skip:
            skip = False
        elif a in GIT_VALUE_OPTS:
            skip = True
        elif not a.startswith("-"):
            return a
    return None


def main():
    role = g.role_arg()
    data = g.read_input()
    cmd = g.shell_command(data)
    if not cmd:
        return
    for name, args in g.invocations(cmd, {"gh", "git"}):
        if name == "gh":
            g.decide("deny", f"Identity guard ({role} agent): plain `gh` runs as the human's GitHub "
                             f"login. Run the same command as `toil-gh {' '.join(args)}`".rstrip() +
                     ", which acts as this agent's GitHub App.")
        verb = git_verb(args)
        if verb in GIT_IDENTITY:
            g.decide("deny", f"Identity guard ({role} agent): `git {verb}` would use the human's name "
                             f"or credentials. Run it as `toil-git {' '.join(args)}`, which commits "
                             "and pushes as this agent's GitHub App.")


if __name__ == "__main__":
    g.run(main)
