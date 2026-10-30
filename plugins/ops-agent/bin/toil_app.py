"""Act on GitHub as an agent's GitHub App instead of as the human who runs it.

Each agent has its own App (for example toil-dev-bot and toil-ops-bot). This script mints a
short-lived installation token from the App's private key and hands it to gh or git without
printing it, so the token never lands in a transcript.

    toil_app.py gh --role dev -- issue list -R toil-lab/checks
    toil_app.py git --role dev -- commit -m "..."  commits as the bot, pushes with the App's token
    toil_app.py git-credential --role dev get      (the git subcommand points git at this)
    toil_app.py identity --role dev                prints the bot's commit name and email
    toil_app.py check --role dev                   mints a token and reports what it can reach

Each plugin's bin/ has toil-gh and toil-git, which call the first two with the plugin's role.

--role defaults to $TOIL_ROLE. Config is ~/.toil/apps.json, or the file named by $TOIL_APPS_CONFIG:

    {
      "org": "toil-lab",
      "roles": {
        "dev": {"app": "toil-dev-bot", "app_id": 5535069, "key": "~/.toil/keys/toil-dev-bot*.pem"},
        "ops": {"app": "toil-ops-bot", "app_id": 5535114, "key": "~/.toil/keys/toil-ops-bot*.pem"}
      }
    }

Tokens are cached in ~/.toil/cache/<role>.json and reused until 10 minutes before they expire
(GitHub issues them for one hour). Signing uses the openssl command, so the script needs only the
Python standard library. Set $TOIL_OPENSSL if openssl isn't on PATH.
"""
import argparse, base64, calendar, glob, json, os, shutil, subprocess, sys, time, urllib.error, urllib.request

API = "https://api.github.com"
REFRESH_MARGIN = 600  # seconds before expiry to mint a new token
WINDOWS_OPENSSL = [r"C:\Program Files\Git\mingw64\bin\openssl.exe", r"C:\Program Files\Git\usr\bin\openssl.exe"]


class Error(Exception):
    pass


def home(*parts):
    return os.path.join(os.path.expanduser("~"), ".toil", *parts)


def load_config(role):
    path = os.environ.get("TOIL_APPS_CONFIG") or home("apps.json")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        raise Error(f"no App config at {path}; see the top of {os.path.basename(__file__)} for its format")
    if role not in cfg.get("roles", {}):
        raise Error(f"role {role!r} is not in {path}")
    r = dict(cfg["roles"][role])
    r["org"] = cfg["org"]
    return r


def key_path(pattern):
    """Newest file matching the key pattern, so a rotated key takes over without a config edit."""
    matches = glob.glob(os.path.expanduser(pattern))
    if not matches:
        raise Error(f"no private key matches {pattern}")
    return max(matches, key=os.path.getmtime)


def openssl():
    found = os.environ.get("TOIL_OPENSSL") or shutil.which("openssl")
    if not found and os.name == "nt":
        found = next((p for p in WINDOWS_OPENSSL if os.path.isfile(p)), None)
    if not found:
        raise Error("openssl not found; install it or set TOIL_OPENSSL")
    return found


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def app_jwt(app_id, key, now=None):
    """RS256 JWT that authenticates as the App itself. Valid 9 minutes, backdated 60 s for clock skew."""
    now = int(now if now is not None else time.time())
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps({"iat": now - 60, "exp": now + 540, "iss": str(app_id)},
                                separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    r = subprocess.run([openssl(), "dgst", "-sha256", "-sign", key, "-binary"],
                       input=signing_input, capture_output=True)
    if r.returncode != 0:
        raise Error(f"openssl could not sign with {key}: {r.stderr.decode(errors='replace').strip()}")
    return f"{header}.{payload}.{b64url(r.stdout)}"


def api(method, path, bearer):
    req = urllib.request.Request(API + path, method=method, headers={
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "toil-app",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise Error(f"GitHub {method} {path} returned {e.code}: {e.read().decode(errors='replace')[:200]}")
    except urllib.error.URLError as e:
        raise Error(f"GitHub {method} {path} failed: {e.reason}")


def parse_time(stamp):
    return calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))


def read_cache(role, now):
    try:
        with open(home("cache", f"{role}.json"), encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError):
        return None
    if c.get("expires", 0) - REFRESH_MARGIN > now:
        return c
    return None


def write_cache(role, token, expires):
    os.makedirs(home("cache"), exist_ok=True)
    path = home("cache", f"{role}.json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"token": token, "expires": expires}, f)


def token(role, now=None):
    """Installation token for the role's App, from the cache when it has 10+ minutes left."""
    now = int(now if now is not None else time.time())
    cached = read_cache(role, now)
    if cached:
        return cached["token"], cached["expires"]
    cfg = load_config(role)
    jwt = app_jwt(cfg["app_id"], key_path(cfg["key"]), now)
    inst = api("GET", f"/orgs/{cfg['org']}/installation", jwt)
    t = api("POST", f"/app/installations/{inst['id']}/access_tokens", jwt)
    expires = parse_time(t["expires_at"])
    write_cache(role, t["token"], expires)
    return t["token"], expires


def identity(role):
    """Commit name and email that GitHub links to the App's bot account."""
    cfg = load_config(role)
    login = f"{cfg['app']}[bot]"
    user_id = cfg.get("bot_user_id")
    if not user_id:
        user_id = api("GET", f"/users/{urllib.request.quote(login)}", token(role)[0])["id"]
    return login, f"{user_id}+{login}@users.noreply.github.com"


def real_gh():
    """The gh binary, skipping any gh wrapper that lives next to this script."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep)
                           if p and os.path.abspath(p) != here)
    found = shutil.which("gh", path=path)
    if not found:
        raise Error("gh not found on PATH")
    return found


def cmd_gh(role, args):
    env = dict(os.environ, GH_TOKEN=token(role)[0])
    env.pop("GITHUB_TOKEN", None)
    return subprocess.call([real_gh()] + args, env=env)


def cmd_git_credential(role, op):
    """git credential helper protocol: answer 'get' for github.com, ignore 'store' and 'erase'."""
    attrs = dict(line.split("=", 1) for line in sys.stdin.read().splitlines() if "=" in line)
    if op != "get" or attrs.get("host") != "github.com":
        return 0
    sys.stdout.write(f"username=x-access-token\npassword={token(role)[0]}\n")
    return 0


def cmd_check(role):
    cfg = load_config(role)
    tok, expires = token(role)
    repos = api("GET", "/installation/repositories?per_page=100", tok)
    names = sorted(r["name"] for r in repos["repositories"])
    left = (expires - int(time.time())) // 60
    print(f"{cfg['app']} on {cfg['org']}: token valid {left} more minutes, {repos['total_count']} repos: "
          + ", ".join(names))
    return 0


def git_args(role, args):
    """git with the App's credential helper (replacing any other for github.com) and bot identity."""
    name, email = identity(role)
    script = os.path.abspath(__file__).replace("\\", "/")
    python = sys.executable.replace("\\", "/")
    helper = f'!"{python}" "{script}" git-credential --role {role}'
    config = ["-c", "credential.https://github.com.helper=",
              "-c", f"credential.https://github.com.helper={helper}",
              "-c", f"user.name={name}", "-c", f"user.email={email}"]
    env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
               GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email)
    return ["git"] + config + args, env


def cmd_git(role, args):
    argv, env = git_args(role, args)
    return subprocess.call(argv, env=env)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("gh", "git", "git-credential", "identity", "check"):
        s = sub.add_parser(name)
        s.add_argument("--role", default=os.environ.get("TOIL_ROLE"))
        if name in ("gh", "git"):
            s.add_argument("args", nargs=argparse.REMAINDER)
        if name == "git-credential":
            s.add_argument("op")
    a = p.parse_args(argv)
    if not a.role:
        p.error("--role is required when TOIL_ROLE is not set")
    try:
        if a.cmd in ("gh", "git"):
            args = a.args[1:] if a.args[:1] == ["--"] else a.args
            return (cmd_gh if a.cmd == "gh" else cmd_git)(a.role, args)
        if a.cmd == "git-credential":
            return cmd_git_credential(a.role, a.op)
        if a.cmd == "identity":
            print("\n".join(identity(a.role)))
            return 0
        return cmd_check(a.role)
    except Error as e:
        sys.stderr.write(f"toil_app: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
