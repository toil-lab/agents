"""The plugins' copies of shared/hooks and contract/ match their sources, and the hook configs
point at files that exist."""
import json, os, re, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SyncTest(unittest.TestCase):
    def test_copies_match_sources(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sync_shared.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_hook_commands_reference_existing_guards(self):
        for plugin in ("dev-agent", "ops-agent"):
            plugin_dir = os.path.join(ROOT, "plugins", plugin)
            with open(os.path.join(plugin_dir, "hooks", "hooks.json"), encoding="utf-8") as f:
                cfg = json.load(f)
            commands = [h["command"] for entries in cfg["hooks"].values() for e in entries for h in e["hooks"]]
            self.assertTrue(commands)
            for c in commands:
                with self.subTest(plugin=plugin, command=c):
                    m = re.search(r'hooks/py"\s+(\S+\.py)', c)
                    self.assertIsNotNone(m, "hook commands run a guard through the py launcher")
                    self.assertTrue(os.path.isfile(os.path.join(plugin_dir, "hooks", m.group(1))))


if __name__ == "__main__":
    unittest.main()
