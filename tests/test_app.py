"""Tests for shared/bin/toil_app.py that need openssl but no network."""
import base64, io, json, os, subprocess, sys, tempfile, time, unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared", "bin"))
import toil_app  # noqa: E402


def unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class AppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name
        patcher = mock.patch.object(toil_app, "home", lambda *p: os.path.join(self.dir, *p))
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_key(self, name="app.pem"):
        path = os.path.join(self.dir, name)
        subprocess.run([toil_app.openssl(), "genrsa", "-out", path, "2048"], check=True, capture_output=True)
        return path

    def test_jwt_is_signed_by_the_key(self):
        key = self.make_key()
        jwt = toil_app.app_jwt(12345, key, now=1_000_000)
        header, payload, sig = jwt.split(".")
        self.assertEqual(json.loads(unb64(header)), {"alg": "RS256", "typ": "JWT"})
        self.assertEqual(json.loads(unb64(payload)), {"iat": 999_940, "exp": 1_000_540, "iss": "12345"})
        pub = os.path.join(self.dir, "pub.pem")
        subprocess.run([toil_app.openssl(), "rsa", "-in", key, "-pubout", "-out", pub], check=True, capture_output=True)
        sig_file = os.path.join(self.dir, "sig")
        with open(sig_file, "wb") as f:
            f.write(unb64(sig))
        r = subprocess.run([toil_app.openssl(), "dgst", "-sha256", "-verify", pub, "-signature", sig_file],
                           input=f"{header}.{payload}".encode(), capture_output=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_newest_key_wins(self):
        old = self.make_key("bot.2026-01-01.pem")
        new = self.make_key("bot.2026-06-01.pem")
        os.utime(old, (1, 1))
        self.assertEqual(toil_app.key_path(os.path.join(self.dir, "bot*.pem")), new)

    def test_missing_key_is_an_error(self):
        with self.assertRaises(toil_app.Error):
            toil_app.key_path(os.path.join(self.dir, "nothing*.pem"))

    def test_cache_reused_until_ten_minutes_before_expiry(self):
        now = int(time.time())
        toil_app.write_cache("dev", "tok", now + 3600)
        self.assertEqual(toil_app.token("dev", now=now), ("tok", now + 3600))
        with mock.patch.object(toil_app, "load_config", side_effect=toil_app.Error("would mint")):
            with self.assertRaises(toil_app.Error):
                toil_app.token("dev", now=now + 3600 - 599)

    def test_expires_at_parses_as_utc(self):
        self.assertEqual(toil_app.parse_time("1970-01-02T00:00:00Z"), 86400)

    def credential(self, stdin, op="get"):
        out = io.StringIO()
        with mock.patch.object(toil_app, "token", return_value=("tok", 0)), \
                mock.patch("sys.stdin", io.StringIO(stdin)), mock.patch("sys.stdout", out):
            self.assertEqual(toil_app.cmd_git_credential("dev", op), 0)
        return out.getvalue()

    def test_credential_answers_github_only(self):
        self.assertEqual(self.credential("protocol=https\nhost=github.com\n"),
                         "username=x-access-token\npassword=tok\n")
        self.assertEqual(self.credential("protocol=https\nhost=gitlab.com\n"), "")
        self.assertEqual(self.credential("protocol=https\nhost=github.com\n", op="store"), "")

    def test_git_resets_other_credential_helpers_and_sets_identity(self):
        with mock.patch.object(toil_app, "identity", return_value=("bot[bot]", "1+bot[bot]@users.noreply.github.com")):
            argv, env = toil_app.git_args("dev", ["commit", "-m", "x"])
        self.assertEqual(argv[:3], ["git", "-c", "credential.https://github.com.helper="])
        self.assertTrue(argv[4].startswith("credential.https://github.com.helper=!"))
        self.assertIn("git-credential --role dev", argv[4])
        self.assertEqual(argv[-3:], ["commit", "-m", "x"])
        self.assertEqual(env["GIT_AUTHOR_EMAIL"], "1+bot[bot]@users.noreply.github.com")
        self.assertEqual(env["GIT_COMMITTER_NAME"], "bot[bot]")

    def test_unknown_role_is_an_error(self):
        cfg = os.path.join(self.dir, "apps.json")
        with open(cfg, "w") as f:
            json.dump({"org": "o", "roles": {"dev": {}}}, f)
        with mock.patch.dict(os.environ, {"TOIL_APPS_CONFIG": cfg}):
            with self.assertRaises(toil_app.Error):
                toil_app.load_config("ops")


if __name__ == "__main__":
    unittest.main()
