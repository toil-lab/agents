"""PreToolUse guard for shared machines: commands that add CPU or memory load stop at a permission
prompt, and the agent states the expected load before the human approves.

Usage in hooks.json: host_load_guard.py
Caught: k3d cluster or node create/start, docker build/run/compose up, helm install/upgrade,
kubectl apply/create/run/scale, k6 run, terraform or tofu apply, and go test with benchmarks.
On a dedicated machine, set TOIL_HOST_SHARED=0 in the environment to turn the guard off.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guardlib as g


def adds_load(name, args):
    """A short label if this call adds load on the host, else None."""
    pos = g.positionals(args)
    first = pos[0] if pos else ""
    second = pos[1] if len(pos) > 1 else ""
    if name == "k3d" and first in ("cluster", "node") and second in ("create", "start"):
        return f"k3d {first} {second}"
    if name == "docker":
        if first in ("build", "run"):
            return f"docker {first}"
        if first == "buildx" and "build" in pos:
            return "docker buildx build"
        if first == "compose" and "up" in pos:
            return "docker compose up"
    if name == "docker-compose" and "up" in pos:
        return "docker-compose up"
    if name == "helm" and first in ("install", "upgrade"):
        return f"helm {first}"
    if name == "kubectl" and first in ("apply", "create", "run", "scale"):
        return f"kubectl {first}"
    if name == "k6" and first == "run":
        return "k6 run"
    if name in ("terraform", "tofu") and first == "apply":
        return f"{name} apply"
    if name == "go" and first == "test" and any(a.startswith("-bench") for a in args):
        return "go test -bench"
    return None


def main():
    if os.environ.get("TOIL_HOST_SHARED", "1") == "0":
        return
    data = g.read_input()
    cmd = g.shell_command(data)
    if not cmd:
        return
    names = {"k3d", "docker", "docker-compose", "helm", "kubectl", "k6", "terraform", "tofu", "go"}
    hits = sorted({label for name, args in g.invocations(cmd, names) if (label := adds_load(name, args))})
    if hits:
        g.decide("ask", "Host load guard: " + ", ".join(hits) + " adds CPU or memory load on a shared "
                 "machine. The agent states the expected RAM and CPU, and how long it lasts, before "
                 "this is approved.")


if __name__ == "__main__":
    g.run(main)
