"""PreToolUse guard: keep each agent inside its own area of ownership.

Usage in hooks.json: scope_guard.py --role dev|ops

Reads the toil.json of the repo being edited (kind: app, platform, or agents) and refuses edits
outside the role's area:

  role  app repo                         platform repo   agents repo
  dev   everything except .github/       nothing         everything except hooks/, bin/
        and CODEOWNERS
  ops   only .github/ and CODEOWNERS     everything      everything except hooks/, bin/

No agent edits toil.json, which holds these rules. Edit, Write, MultiEdit, and NotebookEdit are
checked, and so are shell writes through `>`/`>>` redirection, tee, and PowerShell Set-Content,
Add-Content, and Out-File. Other ways of writing files from a shell are not parsed; CODEOWNERS
and branch protection catch those at review.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guardlib as g

FILE_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
REDIRECT = re.compile(r"(?<![0-9&<])>>?\s*(['\"]?)([^\s'\";|&<>]+)\1")
DISCARD = {"/dev/null", "$null", "nul", "null"}
PS_WRITERS = {"set-content", "add-content", "out-file"}


def refusal(role, kind, rel):
    """None if `role` may edit `rel` in a repo of this kind, else the reason it may not."""
    if rel == "toil.json":
        return "toil.json sets this repo's ownership rules, and only a human changes it"
    if kind == "agents":
        if re.match(r"(shared|plugins/[^/]+)/(hooks|bin)/", rel):
            return ("agents do not edit the guard hooks that limit them or the App helper that sets "
                    "their GitHub identity; a human changes these in a session without the agent plugins")
        return None
    if kind == "platform":
        if role == "ops":
            return None
        return "the platform repo belongs to the DevOps agent; open an issue there describing what you need"
    if kind == "app":
        ci_or_owners = rel.startswith(".github/") or rel == "CODEOWNERS"
        if role == "dev" and ci_or_owners:
            return "CI workflows and CODEOWNERS belong to the DevOps agent; ask for the change in an issue on the platform repo"
        if role == "ops" and not ci_or_owners:
            return ("application code, the Dockerfile, and service.yaml belong to the developer agent; "
                    "file an issue in this repo with the evidence instead")
    return None


def shell_write_targets(command):
    targets = [m.group(2) for m in REDIRECT.finditer(command)]
    for _, args in g.invocations(command, {"tee"}):
        targets += [a for a in args if not a.startswith("-")]
    for _, args in g.invocations(command, PS_WRITERS):
        p = g.flag_value([a.lower() if a.startswith("-") else a for a in args], ["-path", "-filepath", "-literalpath"])
        if p is None:
            pos = [a for a in args if not a.startswith("-")]
            p = pos[0] if pos else None
        if p:
            targets.append(p)
    return [t for t in targets if t.lower() not in DISCARD]


def main():
    role = g.role_arg()
    data = g.read_input()
    tool = data.get("tool_name", "")
    cwd = data.get("cwd") or os.getcwd()
    if tool in FILE_TOOLS:
        p = (data.get("tool_input") or {}).get(FILE_TOOLS[tool])
        targets = [p] if p else []
    else:
        cmd = g.shell_command(data)
        targets = shell_write_targets(cmd) if cmd else []
    for t in targets:
        path = g.normalize_path(t, cwd)
        root, cfg = g.find_repo(path)
        if not cfg:
            continue
        rel = os.path.relpath(path, root).replace("\\", "/")
        kind = cfg.get("kind")
        why = refusal(role, kind, rel)
        if why:
            g.decide("deny", f"Scope guard ({role} agent): {rel} in the {kind} repo is outside your area: {why}.")


if __name__ == "__main__":
    g.run(main)
