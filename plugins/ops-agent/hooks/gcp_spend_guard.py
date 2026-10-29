"""PreToolUse guard: no Google Cloud spending without a human's approval.

Usage in hooks.json: gcp_spend_guard.py
Asks (permission prompt) on any shell command that:
  - runs gcloud, gsutil, or bq with a verb that creates or changes resources,
  - runs terraform or tofu apply against a config that uses the google provider, or whose
    providers can't be read,
  - points kubectl or helm at a GKE context (gke_...),
  - sends a write request (POST, PUT, PATCH) to *.googleapis.com.
Read-only calls (list, describe, plan, validate) pass. The agent states the expected cost, and
whether it stays inside the free tier, before the prompt is approved.
"""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guardlib as g

MUTATING = {"create", "deploy", "update", "patch", "resize", "enable", "import", "start", "resume",
            "run", "submit", "apply", "link", "scale", "add-iam-policy-binding", "set-iam-policy",
            "set", "mb", "cp", "mv", "rsync", "mk", "load", "insert", "copy", "clone", "restore",
            "upgrade", "attach", "reserve", "purchase", "commit"}
GOOGLE_TF = re.compile(r"hashicorp/google|provider\s+\"google(-beta)?\"|resource\s+\"google_")


def uses_google(d):
    """True if the Terraform config in d uses the google provider; None if there's none to read."""
    files = glob.glob(os.path.join(d, "*.tf")) + glob.glob(os.path.join(d, ".terraform.lock.hcl"))
    if not files:
        return None
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                if GOOGLE_TF.search(fh.read()):
                    return True
        except OSError:
            return None
    return False


def main():
    data = g.read_input()
    cmd = g.shell_command(data)
    if not cmd:
        return
    cwd = data.get("cwd") or os.getcwd()
    reasons = []
    for name, args in g.invocations(cmd, {"gcloud", "gsutil", "bq"}):
        if MUTATING & {p.lower() for p in g.positionals(args)}:
            reasons.append(f"{name} command that can create or change Google Cloud resources")
    for name, args in g.invocations(cmd, {"terraform", "tofu"}):
        if "apply" not in g.positionals(args):
            continue
        chdir = g.flag_value(args, ["-chdir"])
        d = g.normalize_path(chdir, cwd) if chdir else cwd
        uses = uses_google(d)
        if uses is None:
            reasons.append(f"{name} apply where the providers can't be read ({d}), so it may use the google provider")
        elif uses:
            reasons.append(f"{name} apply on a config that uses the google provider ({d})")
    for name, args in g.invocations(cmd, {"kubectl", "helm"}):
        ctx = g.flag_value(args, ["--context", "--kube-context"]) or ""
        if ctx.startswith("gke_"):
            reasons.append(f"{name} against a GKE cluster (load balancers, disks, and node scaling are billed)")
    low = cmd.lower()
    if "googleapis.com" in low and re.search(r"-x\s*(post|put|patch)\b|--data\b|\s-d\s|-method\s+(post|put|patch)\b", low):
        reasons.append("write request to a googleapis.com endpoint")
    if reasons:
        g.decide("ask", "GCP spend guard: " + "; ".join(sorted(set(reasons))) + ". No Google Cloud "
                 "spending without a human's approval. The agent states the expected cost, and whether "
                 "it stays inside the free tier, before this is approved.")


if __name__ == "__main__":
    g.run(main)
