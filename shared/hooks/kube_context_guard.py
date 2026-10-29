"""PreToolUse guard: every kubectl and helm call that reaches the cluster names a claude-* context.

Usage in hooks.json: kube_context_guard.py --role dev|ops

  dev  only claude-<team>-logs contexts, and only read verbs (get, describe, logs, events, top, ...)
  ops  claude-ro or claude-<team>-dev
The admin context, and any other non-claude context, is for humans and is always refused, as is
k9s. Agents may read kubeconfig but not change it. RBAC on each context is the real limit; this
guard stops the mistake before the call is made.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guardlib as g

KUBECTL_READ = {"get", "describe", "logs", "top", "events", "explain", "api-resources",
                "api-versions", "version", "cluster-info", "auth"}
KUBECTL_LOCAL = {"config", "completion", "kustomize", "plugin", "options", "help"}
CONFIG_READ = {"get-contexts", "current-context", "view", "get-clusters", "get-users"}
ROLLOUT_READ = {"status", "history"}
HELM_CLUSTER = {"install", "upgrade", "uninstall", "delete", "rollback", "list", "ls", "status",
                "get", "history", "test"}
HELM_READ = {"list", "ls", "status", "get", "history"}


def context_refusal(ctx, role, reads_only, what):
    if not ctx:
        return f"`{what}` must name a context (claude-* only); the current kubeconfig context is never assumed"
    if not ctx.startswith("claude-"):
        return f"context {ctx} is for humans; agents use claude-* contexts"
    if role == "dev":
        if not re.fullmatch(r"claude-[a-z0-9-]+-logs", ctx):
            return "the developer agent uses its team's claude-<team>-logs context only"
        if not reads_only:
            return (f"`{what}` changes the cluster; the developer agent reads logs and events only "
                    "and asks the DevOps agent for changes in an issue")
    if role == "ops" and not (ctx == "claude-ro" or ctx.endswith("-dev")):
        return "the DevOps agent uses claude-ro or a claude-<team>-dev context"
    return None


def kubectl_refusal(args, role):
    pos = g.positionals(args)
    verb = pos[0] if pos else ""
    if verb in KUBECTL_LOCAL or "--client" in args:
        if verb == "config" and len(pos) > 1 and pos[1] not in CONFIG_READ:
            return f"`kubectl config {pos[1]}` changes kubeconfig; agents only read it"
        return None
    reads_only = verb in KUBECTL_READ or (verb == "rollout" and len(pos) > 1 and pos[1] in ROLLOUT_READ)
    return context_refusal(g.flag_value(args, ["--context"]), role, reads_only, f"kubectl {verb}".strip())


def helm_refusal(args, role):
    pos = g.positionals(args)
    verb = pos[0] if pos else ""
    if verb not in HELM_CLUSTER:
        return None
    return context_refusal(g.flag_value(args, ["--kube-context"]), role, verb in HELM_READ, f"helm {verb}")


def main():
    role = g.role_arg()
    data = g.read_input()
    cmd = g.shell_command(data)
    if not cmd:
        return
    for name, args in g.invocations(cmd, {"kubectl", "helm", "k9s"}):
        if name == "k9s":
            why = "k9s is interactive and uses whatever context is current; use kubectl with a claude-* context"
        elif name == "kubectl":
            why = kubectl_refusal(args, role)
        else:
            why = helm_refusal(args, role)
        if why:
            g.decide("deny", f"Kube context guard ({role} agent): {why}.")


if __name__ == "__main__":
    g.run(main)
