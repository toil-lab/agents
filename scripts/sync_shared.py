"""Copy the shared guards, the App token helper, and the contract into each plugin, or check that the copies match.

Claude Code copies an installed plugin into its plugin cache, and files outside the plugin's own
folder are not copied with it. So each plugin carries its own copy of shared/hooks, shared/bin, and
contract/.
Edit the originals, then run:   python scripts/sync_shared.py
Tests and CI run:               python scripts/sync_shared.py --check
"""
import filecmp, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMON_HOOKS = ["py", "guardlib.py", "scope_guard.py", "kube_context_guard.py", "host_load_guard.py",
                "identity_guard.py"]
BIN = ["toil_app.py"]
CONTRACT = ["service.schema.json", "toil.schema.json", "validate.py"]
PLAN = {
    "dev-agent": {"hooks": COMMON_HOOKS, "bin": BIN, "contract": CONTRACT},
    "ops-agent": {"hooks": COMMON_HOOKS + ["gcp_spend_guard.py"], "bin": BIN, "contract": CONTRACT},
}
SOURCES = {"hooks": os.path.join(ROOT, "shared", "hooks"), "bin": os.path.join(ROOT, "shared", "bin"),
           "contract": os.path.join(ROOT, "contract")}
# Plugin-specific files in synced folders: the hook config, and the shims that fix the role.
KEEP = {"hooks.json", "__pycache__", "toil-gh", "toil-git"}


def pairs():
    for plugin, dirs in PLAN.items():
        for kind, names in dirs.items():
            dest_dir = os.path.join(ROOT, "plugins", plugin, kind)
            for n in names:
                yield os.path.join(SOURCES[kind], n), os.path.join(dest_dir, n)


def stale():
    """Files in a plugin's synced folders that no longer come from a source."""
    out = []
    for plugin, dirs in PLAN.items():
        for kind, names in dirs.items():
            dest_dir = os.path.join(ROOT, "plugins", plugin, kind)
            if os.path.isdir(dest_dir):
                out += [os.path.join(dest_dir, f) for f in os.listdir(dest_dir) if f not in set(names) | KEEP]
    return out


def main(check):
    problems = []
    for src, dest in pairs():
        same = os.path.isfile(dest) and filecmp.cmp(src, dest, shallow=False)
        if same:
            continue
        if check:
            problems.append(f"out of date: {os.path.relpath(dest, ROOT)}")
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
            print(f"copied {os.path.relpath(src, ROOT)} -> {os.path.relpath(dest, ROOT)}")
    for f in stale():
        if check:
            problems.append(f"not from a source: {os.path.relpath(f, ROOT)}")
        else:
            os.remove(f)
            print(f"removed {os.path.relpath(f, ROOT)}")
    for p in problems:
        print(p)
    if check and problems:
        print("Run: python scripts/sync_shared.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
