"""Tests for the guard hooks in shared/hooks. Run: python -m unittest discover -s tests"""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "shared", "hooks")


def run(script, command=None, file_path=None, tool=None, cwd=None, role=None, env=None):
    """Run a guard and return its decision: 'allow', 'ask', 'deny', or None for no opinion."""
    if tool is None:
        tool = "Bash" if command is not None else "Edit"
    tool_input = {"command": command} if command is not None else {"file_path": file_path}
    args = [sys.executable, os.path.join(HOOKS, script)] + (["--role", role] if role else [])
    r = subprocess.run(args, input=json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": cwd or ROOT}),
                       capture_output=True, text=True, env={**os.environ, **(env or {})})
    if r.returncode != 0:
        raise AssertionError(f"{script} exited {r.returncode}: {r.stderr}")
    if not r.stdout.strip():
        return None
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]


class Workspace:
    """A temp folder with an app repo, a platform repo, an agents repo, and a folder outside any repo."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = self.tmp.name
        self.repos = {}
        for name, cfg in {"checks": {"kind": "app", "team": "checks"}, "platform": {"kind": "platform"},
                          "agents": {"kind": "agents"}}.items():
            d = os.path.join(base, name)
            os.makedirs(os.path.join(d, ".git"))
            with open(os.path.join(d, "toil.json"), "w") as f:
                json.dump(cfg, f)
            self.repos[name] = d
        self.outside = os.path.join(base, "elsewhere")
        os.makedirs(os.path.join(self.outside, ".git"))

    def path(self, repo, rel):
        return os.path.join(self.repos[repo], *rel.split("/"))


class ScopeGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = Workspace()

    @classmethod
    def tearDownClass(cls):
        cls.ws.tmp.cleanup()

    def edit(self, role, repo, rel):
        return run("scope_guard.py", file_path=self.ws.path(repo, rel), role=role)

    def test_file_edits(self):
        cases = [
            ("dev", "checks", "cmd/probe-worker/main.go", None),
            ("dev", "checks", "service.yaml", None),
            ("dev", "checks", "Dockerfile", None),
            ("dev", "checks", ".github/workflows/ci.yml", "deny"),
            ("dev", "checks", "CODEOWNERS", "deny"),
            ("dev", "checks", "toil.json", "deny"),
            ("dev", "platform", "argocd/root.yaml", "deny"),
            ("ops", "checks", "cmd/probe-worker/main.go", "deny"),
            ("ops", "checks", "service.yaml", "deny"),
            ("ops", "checks", "Dockerfile", "deny"),
            ("ops", "checks", ".github/workflows/ci.yml", None),
            ("ops", "platform", "argocd/root.yaml", None),
            ("ops", "platform", "toil.json", "deny"),
            ("ops", "agents", "plugins/ops-agent/hooks/scope_guard.py", "deny"),
            ("dev", "agents", "shared/hooks/guardlib.py", "deny"),
            ("dev", "agents", "plugins/dev-agent/skills/build-feature/SKILL.md", None),
            ("ops", "agents", "contract/service.schema.json", None),
        ]
        for role, repo, rel, want in cases:
            with self.subTest(role=role, path=f"{repo}/{rel}"):
                self.assertEqual(self.edit(role, repo, rel), want)

    def test_outside_any_repo_is_not_judged(self):
        self.assertIsNone(run("scope_guard.py", file_path=os.path.join(self.ws.outside, "x.txt"), role="ops"))

    def test_other_file_tools(self):
        p = self.ws.path("checks", "notebooks/explore.ipynb")
        r = subprocess.run([sys.executable, os.path.join(HOOKS, "scope_guard.py"), "--role", "ops"],
                           input=json.dumps({"tool_name": "NotebookEdit", "tool_input": {"notebook_path": p}}),
                           capture_output=True, text=True)
        self.assertIn('"deny"', r.stdout)

    def test_shell_writes(self):
        app = self.ws.repos["checks"]
        cases = [
            ("dev", "echo x > .github/workflows/ci.yml", "deny"),
            ("dev", "echo hi >> notes.txt", None),
            ("dev", "go test ./... > /dev/null 2>&1", None),
            ("ops", "cat new.go | tee cmd/main.go", "deny"),
            ("ops", "echo 'name: ci' > .github/workflows/ci.yml", None),
            ("dev", "ls 2>&1", None),
        ]
        for role, cmd, want in cases:
            with self.subTest(role=role, cmd=cmd):
                self.assertEqual(run("scope_guard.py", command=cmd, cwd=app, role=role), want)

    def test_powershell_writes(self):
        app = self.ws.repos["checks"]
        self.assertEqual(run("scope_guard.py", command="Set-Content -Path main.go -Value x", tool="PowerShell",
                             cwd=app, role="ops"), "deny")
        self.assertEqual(run("scope_guard.py", command="'x' | Out-File notes.txt", tool="PowerShell",
                             cwd=app, role="dev"), None)

    @unittest.skipUnless(os.name == "nt", "Git Bash paths only exist on Windows")
    def test_git_bash_paths(self):
        p = self.ws.path("checks", "main.go").replace("\\", "/")
        bash_path = "/" + p[0].lower() + p[2:]
        self.assertEqual(run("scope_guard.py", file_path=bash_path, role="ops"), "deny")


class KubeContextGuardTest(unittest.TestCase):
    def test_commands(self):
        cases = [
            ("ops", "kubectl get pods", "deny"),
            ("ops", "kubectl --context claude-ro get pods -A", None),
            ("ops", "kubectl --context=admin delete pod x", "deny"),
            ("ops", "kubectl --context claude-checks-dev apply -f deploy.yaml", None),
            ("ops", "kubectl --context claude-checks-logs get pods", "deny"),
            ("dev", "kubectl --context claude-checks-logs logs deploy/probe-worker", None),
            ("dev", "kubectl --context claude-checks-logs get events -n checks-dev", None),
            ("dev", "kubectl --context claude-checks-logs rollout status deploy/probe-worker", None),
            ("dev", "kubectl --context claude-checks-logs delete pod x", "deny"),
            ("dev", "kubectl --context claude-ro get pods", "deny"),
            ("dev", "helm --kube-context claude-checks-logs list -n checks-dev", None),
            ("dev", "helm --kube-context claude-checks-logs upgrade x ./chart", "deny"),
            ("ops", "helm upgrade x ./chart", "deny"),
            ("ops", "helm upgrade x ./chart --kube-context claude-checks-dev", None),
            ("ops", "helm template x ./chart", None),
            ("ops", "kubectl config use-context admin", "deny"),
            ("ops", "kubectl config get-contexts", None),
            ("ops", "kubectl version --client", None),
            ("ops", "wsl -d Ubuntu -- kubectl get pods", "deny"),
            ("ops", "bash -c \"kubectl delete ns checks-dev\"", "deny"),
            ("ops", "grep kubectl notes.md", None),
            ("ops", "k9s", "deny"),
            ("dev", "go test ./...", None),
        ]
        for role, cmd, want in cases:
            with self.subTest(role=role, cmd=cmd):
                self.assertEqual(run("kube_context_guard.py", command=cmd, role=role), want)


class HostLoadGuardTest(unittest.TestCase):
    def test_commands(self):
        cases = [
            ("k3d cluster create lab --agents 2", "ask"),
            ("k3d cluster list", None),
            ("docker build -t probe-worker .", "ask"),
            ("docker ps", None),
            ("docker compose up -d", "ask"),
            ("kubectl --context claude-ro get pods", None),
            ("kubectl --context claude-checks-dev apply -f x.yaml", "ask"),
            ("helm upgrade --install x ./chart", "ask"),
            ("k6 run load.js", "ask"),
            ("go test ./...", None),
            ("go test -bench=. ./...", "ask"),
            ("terraform plan", None),
            ("terraform -chdir=infra apply", "ask"),
        ]
        for cmd, want in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(run("host_load_guard.py", command=cmd), want)

    def test_dedicated_machine_switch(self):
        self.assertIsNone(run("host_load_guard.py", command="k3d cluster create lab", env={"TOIL_HOST_SHARED": "0"}))


class GcpSpendGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = cls.tmp.name
        cls.gdir, cls.kdir, cls.edir = (os.path.join(base, n) for n in ("gcp", "k8s", "empty"))
        for d in (cls.gdir, cls.kdir, cls.edir):
            os.makedirs(d)
        with open(os.path.join(cls.gdir, "main.tf"), "w") as f:
            f.write('provider "google" {\n  project = "x"\n}\n')
        with open(os.path.join(cls.kdir, "main.tf"), "w") as f:
            f.write('provider "kubernetes" {\n  config_path = "~/.kube/config"\n}\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_commands(self):
        base = self.tmp.name
        cases = [
            ("gcloud projects list", base, None),
            ("gcloud container clusters describe lab --zone us-central1-a", base, None),
            ("gcloud storage buckets create gs://x --location us-central1", base, "ask"),
            ("gcloud services enable container.googleapis.com", base, "ask"),
            ("wsl -d Ubuntu -- gcloud compute instances create vm1", base, "ask"),
            ("gsutil mb gs://x", base, "ask"),
            ("gsutil ls gs://x", base, None),
            ("terraform plan", self.gdir, None),
            ("terraform apply -auto-approve", self.gdir, "ask"),
            ("terraform -chdir=gcp apply", base, "ask"),
            ("terraform apply", self.kdir, None),
            ("terraform apply", self.edir, "ask"),
            ("kubectl --context gke_proj_us-central1-a_lab apply -f svc.yaml", base, "ask"),
            ("kubectl --context claude-ro get pods", base, None),
            ("curl -X POST https://compute.googleapis.com/compute/v1/projects/x/zones/z/instances", base, "ask"),
            ("curl https://storage.googleapis.com/x/y", base, None),
            ("git status && npm run build", base, None),
            ("grep -r gcloud docs/ | head", base, None),
        ]
        for cmd, cwd, want in cases:
            with self.subTest(cmd=cmd):
                self.assertEqual(run("gcp_spend_guard.py", command=cmd, cwd=cwd), want)


class GuardsIgnoreOtherToolsTest(unittest.TestCase):
    def test_read_tool(self):
        for script in ("kube_context_guard.py", "host_load_guard.py", "gcp_spend_guard.py"):
            with self.subTest(script=script):
                r = subprocess.run([sys.executable, os.path.join(HOOKS, script), "--role", "ops"],
                                   input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x"}}),
                                   capture_output=True, text=True)
                self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))


if __name__ == "__main__":
    unittest.main()
