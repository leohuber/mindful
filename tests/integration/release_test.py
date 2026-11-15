import asyncio
import json
import os
import pty
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Result:
    code: int
    output: str


async def execute(
    args: tuple[str, ...],
    cwd: Path,
    env: dict[str, str],
    answer: str | None,
) -> Result:
    master, slave = pty.openpty() if answer is not None else (None, None)
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            env=env,
            stdin=slave if slave is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        if master is not None and answer is not None:
            os.write(master, (answer + "\n").encode())
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=45)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise
        return Result(process.returncode or 0, output.decode())
    finally:
        if master is not None and slave is not None:
            os.close(master)
            os.close(slave)


@dataclass
class ReleaseRepository:
    root: Path
    remote: Path
    env: dict[str, str]
    log: Path

    def run(self, *args: str, answer: str | None = None, cwd: Path | None = None) -> Result:
        return asyncio.run(execute(args, cwd or self.root, self.env, answer))

    def git(self, *args: str, cwd: Path | None = None) -> str:
        result = self.run("git", *args, cwd=cwd)
        assert result.code == 0, result.output
        return result.output.strip()

    def release(self, *args: str, answer: str | None = None) -> Result:
        return self.run("zsh", "scripts/release.sh", *args, answer=answer)

    def snapshot(self) -> tuple[str, str, str]:
        return (
            self.git("status", "--porcelain"),
            self.git("for-each-ref", "--format=%(refname) %(objectname)"),
            self.git("--git-dir", str(self.remote), "show-ref"),
        )


@pytest.fixture
def repository(tmp_path: Path) -> ReleaseRepository:
    root = tmp_path / "checkout"
    remote = tmp_path / "remote.git"
    tools = tmp_path / "tools"
    home = tmp_path / "home"
    temporary = tmp_path / "temporary"
    github = tmp_path / "github"
    for path in (root, tools, home, temporary, github):
        path.mkdir()
    log = tmp_path / "gh.log"
    real_git = shutil.which("git")
    assert real_git is not None
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
            "GH_LOG": str(log),
            "FAKE_GITHUB": str(github),
            "GIT_TEST_REAL": real_git,
            "GIT_TEST_REMOTE": str(remote),
            "GIT_ALLOW_PROTOCOL": "file",
            "GIT_CONFIG_GLOBAL": str(home / "gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "TMPDIR": str(temporary),
            "UV_TEST_LOG": str(tmp_path / "uv.log"),
        }
    )
    repo = ReleaseRepository(root, remote, env, log)
    (tools / "git").write_text(
        """#!/bin/sh
if [ "$1" = remote ] && [ "$2" = get-url ]; then
    result="$("$GIT_TEST_REAL" "$@")" || exit $?
    if [ "$result" = "$GIT_TEST_REMOTE" ]; then
        echo https://github.com/leohuber/mindful.git
    else
        printf '%s\\n' "$result"
    fi
elif [ "$1" = push ] && [ "$2" = --atomic ] && [ "${TEST_PUSH_MODE:-}" = reject-atomic ]; then
    echo "simulated atomic push rejection" >&2
    exit 1
elif [ "$1" = push ] && [ "$2" = --atomic ] && [ "${TEST_PUSH_MODE:-}" = lost-atomic-response ]; then
    "$GIT_TEST_REAL" "$@" || exit $?
    echo "simulated lost atomic push response" >&2
    exit 1
elif [ "$1" = push ] && [ "$2" != --atomic ] && [ "${TEST_PUSH_MODE:-}" = reject-development ]; then
    echo "simulated development push rejection" >&2
    exit 1
else
    exec "$GIT_TEST_REAL" "$@"
fi
""",
        encoding="utf-8",
    )
    (tools / "git").chmod(0o755)
    repo.git("init", "--bare", str(remote))
    repo.git("init", "-b", "main")
    repo.git("config", "user.name", "Release Test")
    repo.git("config", "user.email", "release-test@example.invalid")
    repo.git("config", "--global", f"url.{remote}.insteadOf", "https://github.com/leohuber/mindful.git")
    repo.git("remote", "add", "origin", "https://github.com/leohuber/mindful.git")
    (root / "scripts").mkdir()
    for name in ("release.sh", "build_addon.py", "install.sh", "__init__.py"):
        shutil.copy2(ROOT / "scripts" / name, root / "scripts")
    shutil.copytree(ROOT / "src" / "mindful", root / "src" / "mindful", ignore=shutil.ignore_patterns("__pycache__"))
    (root / ".gitignore").write_text(".venv/\ndist/\n__pycache__/\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "mindful"\nversion = "0.1.0.dev0"\n', encoding="utf-8")
    (root / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "mindful"\nversion = "0.1.0.dev0"\n\n[[package]]\nname = "other"\nversion = "7.0.0"\n',
        encoding="utf-8",
    )
    (root / "caller.txt").write_text("original checkout", encoding="utf-8")
    (tools / "gh").write_text(
        f"#!{sys.executable}\n"
        """import os
import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
mode = os.environ.get("GH_FAKE_MODE", "")
state = Path(os.environ["FAKE_GITHUB"])
with Path(os.environ["GH_LOG"]).open("a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\\n")
if args[0] == "auth":
    sys.exit(1 if mode == "auth-failure" else 0)
if args[0] == "repo":
    print("other/project" if mode == "wrong-repository" else "leohuber/mindful")
    sys.exit(0)
if args[0] == "api":
    if mode == "api-failure":
        print("HTTP/2.0 503 Unavailable")
        sys.exit(1)
    if mode == "release-exists" or (state / "release-tag").exists():
        print("HTTP/2.0 200 OK")
        sys.exit(0)
    print("HTTP/2.0 404 Not Found")
    sys.exit(1)
if args[:2] == ["release", "create"]:
    if mode == "create-failure":
        sys.exit(1)
    tag = args[2]
    (state / "release-tag").write_text(tag, encoding="utf-8")
    for name in args[3:]:
        if name.startswith("--"):
            break
        source = Path(name)
        if mode == "partial-upload-zip" and source.suffix == ".ankiaddon":
            continue
        shutil.copy2(source, state / source.name)
        if mode in {"partial-upload", "partial-success"}:
            break
    if mode == "mismatched-asset":
        (state / f"mindful-{tag[1:]}.ankiaddon").write_bytes(b"unexpected asset")
    if mode == "mismatched-zip":
        (state / f"mindful-{tag[1:]}.zip").write_bytes(b"unexpected asset")
    if mode in {"partial-upload", "partial-upload-zip", "lost-response"}:
        sys.exit(1)
    sys.exit(0)
if args[:2] == ["release", "view"]:
    if not (state / "release-tag").exists():
        sys.exit(1)
    if "assets" in args:
        for asset in sorted(state.iterdir()):
            if asset.suffix in {".ankiaddon", ".zip"}:
                print(asset.name)
        sys.exit(0)
    print((state / "release-tag").read_text(encoding="utf-8") + (" true" if mode == "draft" else " false"))
    sys.exit(0)
if args[:2] == ["release", "download"]:
    name = args[args.index("--pattern") + 1]
    destination = Path(args[args.index("--dir") + 1])
    source = state / name
    if not source.is_file():
        sys.exit(1)
    shutil.copy2(source, destination / name)
    sys.exit(0)
if args[:2] == ["release", "upload"]:
    source = Path(args[3])
    destination = state / source.name
    if destination.exists():
        sys.exit(1)
    shutil.copy2(source, destination)
    sys.exit(0)
sys.exit(99)
""",
        encoding="utf-8",
    )
    (tools / "uv").write_text(
        f"#!{sys.executable}\n"
        """import os
import sys
import tomllib
from pathlib import Path
from zipfile import ZipFile

args = sys.argv[1:]
with Path(os.environ["UV_TEST_LOG"]).open("a", encoding="utf-8") as log:
    log.write(str(Path.cwd()) + " | " + " ".join(args) + "\\n")
project_path = Path("pyproject.toml")
lock_path = Path("uv.lock")
project = project_path.read_text(encoding="utf-8")
lock = lock_path.read_text(encoding="utf-8")
actual = tomllib.loads(project)["project"]["version"]
current = os.environ.get("UV_FAKE_VERSION", actual)
if args == ["lock", "--check"]:
    package = next(item for item in tomllib.loads(lock)["package"] if item["name"] == "mindful")
    sys.exit(0 if package["version"] == actual else 1)
if args[0] == "version":
    if args == ["version", "--short"]:
        print(current)
        sys.exit(0)
    if "--dry-run" in args:
        bump = args[args.index("--bump") + 1]
        major, minor, patch = (int(value) for value in current.split(".dev")[0].split("."))
        if bump == "stable":
            result = f"{major}.{minor}.{patch}"
        elif bump == "patch":
            result = f"{major}.{minor}.{patch + 1}.dev0"
        elif bump == "minor":
            result = f"{major}.{minor + 1}.0.dev0"
        else:
            result = f"{major + 1}.0.0.dev0"
        print(result)
        sys.exit(0)
    new = args[1]
    if os.environ.get("TEST_CALLER_EDIT"):
        Path(os.environ["TEST_CALLER_EDIT"]).write_text("concurrent caller change", encoding="utf-8")
    project_path.write_text(project.replace(f'version = "{actual}"', f'version = "{new}"', 1), encoding="utf-8")
    lock = lock.replace(f'name = "mindful"\\nversion = "{actual}"', f'name = "mindful"\\nversion = "{new}"', 1)
    if os.environ.get("TEST_UV_UNRELATED"):
        lock = lock.replace('version = "7.0.0"', 'version = "7.0.1"')
    lock_path.write_text(lock, encoding="utf-8")
    sys.exit(0)
if args[0] == "run":
    if args[1] == "python":
        if len(args) > 2 and args[2] == "scripts/build_addon.py":
            if actual != "0.1.0":
                sys.exit(1)
            mode = os.environ.get("TEST_BUILD_MODE", "")
            if mode == "fail":
                sys.exit(1)
            if mode == "invalid":
                Path("dist").mkdir(exist_ok=True)
                with ZipFile("dist/mindful.ankiaddon", "w") as archive:
                    archive.writestr("__init__.py", "invalid")
                sys.exit(0)
        os.execv(sys.executable, [sys.executable, *args[2:]])
    if actual != "0.1.0":
        sys.exit(1)
    if args[1] == "pytest" and os.environ.get("TEST_CALLER_EDIT"):
        Path(os.environ["TEST_CALLER_EDIT"]).write_text("concurrent caller change", encoding="utf-8")
    gate = " ".join(args[1:3])
    if os.environ.get("TEST_QUALITY_FAIL") == gate:
        sys.exit(1)
    sys.exit(0)
sys.exit(99)
""",
        encoding="utf-8",
    )
    (tools / "uname").write_text('#!/bin/sh\nprintf "%s\\n" "${TEST_PLATFORM:-Darwin}"\n', encoding="utf-8")
    (tools / "ps").write_text(
        """#!/bin/sh
if [ "${TEST_ANKI_RUNNING:-}" = 1 ]; then
    echo /Applications/Anki.app/Contents/MacOS/Anki
else
    echo /usr/bin/other
fi
""",
        encoding="utf-8",
    )
    if sys.platform != "darwin":
        (tools / "plutil").write_text(
            f"#!{sys.executable}\n"
            """import json, sys
key = sys.argv[sys.argv.index("-extract") + 1]
path = sys.argv[-1]
with (sys.stdin if path == "-" else open(path, encoding="utf-8")) as source:
    print(json.load(source)[key])
""",
            encoding="utf-8",
        )
        (tools / "stat").write_text(
            f"#!{sys.executable}\n"
            """import os, sys
entry = os.stat(sys.argv[-1])
if sys.argv[2] == "%p:%m:%u:%g":
    print(f"{entry.st_mode:o}:{int(entry.st_mtime)}:{entry.st_uid}:{entry.st_gid}")
else:
    print(f"{entry.st_dev}:{entry.st_ino}")
""",
            encoding="utf-8",
        )
    for tool in tools.iterdir():
        tool.chmod(0o755)
    repo.git("add", ".")
    repo.git("commit", "-m", "Initial")
    repo.git("push", "origin", "main")
    repo.git("--git-dir", str(remote), "symbolic-ref", "HEAD", "refs/heads/main")
    return repo


@pytest.mark.parametrize(("bump", "version"), [("patch", "0.1.1.dev0"), ("minor", "0.2.0.dev0"), ("major", "1.0.0.dev0")])
def test_preview_is_read_only_and_shows_release_plan(repository: ReleaseRepository, bump: str, version: str) -> None:
    before = repository.snapshot()

    result = repository.release("--dry-run", "--next-bump", bump)

    assert result.code == 0, result.output
    assert "leohuber/mindful" in result.output
    assert "Branch: main" in result.output
    assert "Release version: 0.1.0" in result.output
    assert f"Next development version: {version}" in result.output
    assert "Tag: v0.1.0" in result.output
    assert "mindful-0.1.0.ankiaddon, mindful-0.1.0.zip" in result.output
    assert repository.snapshot() == before
    assert "release create" not in repository.log.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ("dirty", "working tree is dirty"),
        ("branch", "current branch must be main"),
        ("remote", "must match origin/main"),
        ("local-tag", "already exists locally"),
        ("remote-tag", "already exists on origin"),
        ("installer", "executable installer"),
        ("untracked-builder", "must be tracked"),
        ("wrong-remote", "expected GitHub repository"),
    ],
)
def test_preflight_rejects_unsafe_repository_state(repository: ReleaseRepository, change: str, error: str, tmp_path: Path) -> None:
    if change == "dirty":
        (repository.root / "untracked").write_text("change", encoding="utf-8")
    elif change == "branch":
        repository.git("switch", "-c", "other")
    elif change == "remote":
        other = tmp_path / "other"
        repository.git("clone", str(repository.remote), str(other))
        repository.git("config", "user.name", "Release Test", cwd=other)
        repository.git("config", "user.email", "release-test@example.invalid", cwd=other)
        (other / "new").write_text("change", encoding="utf-8")
        repository.git("add", "new", cwd=other)
        repository.git("commit", "-m", "Remote change", cwd=other)
        repository.git("push", "origin", "HEAD:main", cwd=other)
    elif change == "local-tag":
        repository.git("tag", "v0.1.0")
    elif change == "remote-tag":
        repository.git("push", "origin", "HEAD:refs/tags/v0.1.0")
    elif change == "installer":
        (repository.root / "scripts" / "install.sh").chmod(0o644)
        repository.git("add", "scripts/install.sh")
        repository.git("commit", "-m", "Installer not executable")
        repository.git("push", "origin", "main")
    elif change == "untracked-builder":
        repository.git("rm", "scripts/build_addon.py")
        repository.git("commit", "-m", "Remove builder")
        repository.git("push", "origin", "main")
    elif change == "wrong-remote":
        repository.git("remote", "set-url", "--push", "origin", "https://github.com/other/project.git")

    before = repository.snapshot()
    result = repository.release("--dry-run")

    assert result.code != 0, result.output
    assert error in result.output
    assert repository.snapshot() == before


@pytest.mark.parametrize(
    ("mode", "error"),
    [
        ("auth-failure", "authentication is required"),
        ("wrong-repository", "Expected GitHub repository"),
        ("release-exists", "already exists"),
        ("api-failure", "Cannot verify"),
        ("stable-version", "development version"),
    ],
)
def test_preflight_rejects_missing_external_prerequisites(repository: ReleaseRepository, mode: str, error: str) -> None:
    if mode == "stable-version":
        repository.env["UV_FAKE_VERSION"] = "0.1.0"
    else:
        repository.env["GH_FAKE_MODE"] = mode
    before = repository.snapshot()

    result = repository.release("--dry-run")

    assert result.code != 0, result.output
    assert error in result.output
    assert repository.snapshot() == before


@pytest.mark.parametrize("answer", [None, "", "no"])
def test_missing_or_declined_confirmation_makes_no_release_changes(repository: ReleaseRepository, answer: str | None) -> None:
    before = repository.snapshot()

    result = repository.release("--next-bump", "patch", answer=answer)

    assert result.code != 0, result.output
    assert "terminal" in result.output.lower() if answer is None else "cancelled" in result.output.lower()
    assert repository.snapshot() == before
    assert "release create" not in repository.log.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("bump", "next_version"),
    [("patch", "0.1.1.dev0"), ("minor", "0.2.0.dev0"), ("major", "1.0.0.dev0")],
)
def test_release_isolates_caller_and_publishes_verified_assets(repository: ReleaseRepository, bump: str, next_version: str) -> None:
    original = repository.git("rev-parse", "HEAD")
    repository.env["TEST_CALLER_EDIT"] = str(repository.root / "caller.txt")

    result = repository.release("--next-bump", bump, answer="release")

    assert result.code == 0, result.output
    assert repository.git("rev-parse", "HEAD") == original
    assert (repository.root / "caller.txt").read_text(encoding="utf-8") == "concurrent caller change"
    assert repository.git("status", "--porcelain") == "M caller.txt"
    remote = ("--git-dir", str(repository.remote))
    assert repository.git(*remote, "cat-file", "-t", "refs/tags/v0.1.0") == "tag"
    stable = repository.git(*remote, "rev-parse", "refs/tags/v0.1.0^{}")
    development = repository.git(*remote, "rev-parse", "refs/heads/main")
    assert repository.git(*remote, "rev-parse", f"{stable}^") == original
    assert repository.git(*remote, "rev-parse", f"{development}^") == stable
    assert 'version = "0.1.0"\n' in repository.git(*remote, "show", f"{stable}:pyproject.toml") + "\n"
    assert f'version = "{next_version}"\n' in repository.git(*remote, "show", f"{development}:pyproject.toml") + "\n"
    assert f'name = "mindful"\nversion = "{next_version}"' in repository.git(*remote, "show", f"{development}:uv.lock")

    github = Path(repository.env["FAKE_GITHUB"])
    standalone = github / "mindful-0.1.0.ankiaddon"
    bundle = github / "mindful-0.1.0.zip"
    with ZipFile(standalone) as archive:
        assert "__init__.py" in archive.namelist()
        assert "manifest.json" in archive.namelist()
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["package"] == "mindful"
        assert "version" not in manifest
    with ZipFile(bundle) as archive:
        assert set(archive.namelist()) == {
            "mindful-0.1.0/",
            "mindful-0.1.0/install.sh",
            "mindful-0.1.0/mindful-0.1.0.ankiaddon",
        }
        assert archive.read("mindful-0.1.0/mindful-0.1.0.ankiaddon") == standalone.read_bytes()
        assert archive.getinfo("mindful-0.1.0/install.sh").external_attr >> 16 & stat.S_IXUSR
    extracted = github / "extracted"
    extracted.mkdir()
    extraction = repository.run("unzip", "-q", str(bundle), "-d", str(extracted))
    assert extraction.code == 0, extraction.output
    assert os.access(extracted / "mindful-0.1.0" / "install.sh", os.X_OK)
    assert (extracted / "mindful-0.1.0" / "mindful-0.1.0.ankiaddon").read_bytes() == standalone.read_bytes()
    log = repository.log.read_text(encoding="utf-8")
    assert "--verify-tag" in log
    assert "--generate-notes" in log
    assert "install.sh" in log
    assert "https://ankiweb.net/shared/addons" in log
    release_url = "https://github.com/leohuber/mindful/releases/download/v0.1.0/"
    assert f"Standalone archive: {release_url}mindful-0.1.0.ankiaddon" in result.output
    assert f"macOS installer ZIP: {release_url}mindful-0.1.0.zip" in result.output
    assert "git merge --ff-only FETCH_HEAD" in result.output
    assert len(repository.git("worktree", "list", "--porcelain").split("worktree ")) == 2
    gate_log = Path(repository.env["UV_TEST_LOG"]).read_text(encoding="utf-8").splitlines()
    for gate in ("run pytest tests", "run ruff check", "run ruff format", "run pyrefly check", "run lint-imports"):
        matching = [line for line in gate_log if f" | {gate}" in line]
        assert len(matching) == 1
        assert matching[0].split(" | ")[0] != str(repository.root)


def retained_release_area(output: str) -> Path:
    prefix = "Retained release area: "
    for line in output.splitlines():
        if line.startswith(prefix):
            area = Path(line.removeprefix(prefix))
            assert (area / "mindful-0.1.0.ankiaddon").is_file()
            assert (area / "mindful-0.1.0.zip").is_file()
            return area
    pytest.fail(f"Release area not reported:\n{output}")


def assert_remote_at_stable_release(repository: ReleaseRepository) -> str:
    remote = ("--git-dir", str(repository.remote))
    stable = repository.git(*remote, "rev-parse", "refs/tags/v0.1.0^{}")
    assert repository.git(*remote, "cat-file", "-t", "refs/tags/v0.1.0") == "tag"
    assert repository.git(*remote, "rev-parse", "refs/heads/main") == stable
    assert 'version = "0.1.0"' in repository.git(*remote, "show", f"{stable}:pyproject.toml")
    return stable


def test_rejected_atomic_push_does_not_publish_or_update_either_ref(repository: ReleaseRepository) -> None:
    original = repository.git("rev-parse", "HEAD")
    hook = repository.remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert "atomic branch-and-tag push failed" in result.output
    assert "Last confirmed state: annotated tag created locally" in result.output
    assert repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/heads/main") == original
    tag = repository.run("git", "--git-dir", str(repository.remote), "show-ref", "--verify", "refs/tags/v0.1.0")
    assert tag.code != 0
    assert "release create" not in repository.log.read_text(encoding="utf-8")
    retained_release_area(result.output)
    stable = repository.git("rev-parse", "refs/tags/v0.1.0^{}")
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    repository.git("push", "--atomic", "origin", f"{stable}:refs/heads/main", "refs/tags/v0.1.0:refs/tags/v0.1.0")
    assert assert_remote_at_stable_release(repository) == stable


def test_lost_atomic_push_response_preserves_remote_state_for_inspection(repository: ReleaseRepository) -> None:
    repository.env["TEST_PUSH_MODE"] = "lost-atomic-response"

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert "outcome is uncertain" in result.output
    assert "Last confirmed state: annotated tag created locally" in result.output
    assert_remote_at_stable_release(repository)
    assert "release create" not in repository.log.read_text(encoding="utf-8")
    assert "do not overwrite mismatched assets or blindly retry" in result.output
    retained_release_area(result.output)


@pytest.mark.parametrize(
    ("mode", "present", "missing"),
    [
        ("partial-upload", "mindful-0.1.0.ankiaddon", "mindful-0.1.0.zip"),
        ("partial-upload-zip", "mindful-0.1.0.zip", "mindful-0.1.0.ankiaddon"),
        ("partial-success", "mindful-0.1.0.ankiaddon", "mindful-0.1.0.zip"),
    ],
)
def test_partial_upload_reports_missing_asset_without_advancing(repository: ReleaseRepository, mode: str, present: str, missing: str) -> None:
    repository.env["GH_FAKE_MODE"] = mode

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert_remote_at_stable_release(repository)
    assert f"GitHub asset {present}:" in result.output
    assert f"GitHub asset {missing}: missing from the inspected release" in result.output
    assert "Upload only an asset confirmed missing" in result.output
    area = retained_release_area(result.output)
    github = Path(repository.env["FAKE_GITHUB"])
    assert (github / present).read_bytes() == (area / present).read_bytes()
    assert not (github / missing).exists()
    upload = repository.run("gh", "release", "upload", "v0.1.0", str(area / missing), "--repo", "leohuber/mindful")
    assert upload.code == 0, upload.output
    assert (github / missing).read_bytes() == (area / missing).read_bytes()
    duplicate = repository.run("gh", "release", "upload", "v0.1.0", str(area / present), "--repo", "leohuber/mindful")
    assert duplicate.code != 0
    assert (github / present).read_bytes() == (area / present).read_bytes()


@pytest.mark.parametrize(
    ("mode", "mismatched"),
    [("mismatched-asset", "mindful-0.1.0.ankiaddon"), ("mismatched-zip", "mindful-0.1.0.zip")],
)
def test_mismatched_published_asset_is_not_overwritten(repository: ReleaseRepository, mode: str, mismatched: str) -> None:
    repository.env["GH_FAKE_MODE"] = mode

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert_remote_at_stable_release(repository)
    assert f"GitHub asset {mismatched}: downloaded but DOES NOT MATCH" in result.output
    assert "do not overwrite mismatched assets" in result.output
    area = retained_release_area(result.output)
    assert (Path(repository.env["FAKE_GITHUB"]) / mismatched).read_bytes() != (area / mismatched).read_bytes()


def test_lost_github_response_requires_asset_inspection_before_retry(repository: ReleaseRepository) -> None:
    repository.env["GH_FAKE_MODE"] = "lost-response"

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert "outcome may be uncertain" in result.output
    assert_remote_at_stable_release(repository)
    area = retained_release_area(result.output)
    github = Path(repository.env["FAKE_GITHUB"])
    for name in ("mindful-0.1.0.ankiaddon", "mindful-0.1.0.zip"):
        assert f"GitHub asset {name}: present; identity not yet verified" in result.output
        assert (github / name).read_bytes() == (area / name).read_bytes()
    assert repository.log.read_text(encoding="utf-8").count("release create") == 1


def test_missing_release_can_be_completed_from_retained_worktree(repository: ReleaseRepository) -> None:
    repository.env["GH_FAKE_MODE"] = "create-failure"

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    stable = assert_remote_at_stable_release(repository)
    area = retained_release_area(result.output)
    github = Path(repository.env["FAKE_GITHUB"])
    assert not (github / "release-tag").exists()
    del repository.env["GH_FAKE_MODE"]
    create = repository.run(
        "gh",
        "release",
        "create",
        "v0.1.0",
        str(area / "mindful-0.1.0.ankiaddon"),
        str(area / "mindful-0.1.0.zip"),
        "--repo",
        "leohuber/mindful",
        "--verify-tag",
        "--title",
        "Mindful 0.1.0",
        "--generate-notes",
        "--notes",
        "Install the standalone .ankiaddon; on macOS, extract the ZIP and run install.sh.",
    )
    assert create.code == 0, create.output
    for name in ("mindful-0.1.0.ankiaddon", "mindful-0.1.0.zip"):
        assert (github / name).read_bytes() == (area / name).read_bytes()

    worktree = area / "worktree"
    assert repository.git("rev-parse", "HEAD", cwd=worktree) == stable
    assert repository.git("status", "--porcelain", cwd=worktree) == ""
    version = repository.run("uv", "version", "0.1.1.dev0", "--no-sync", cwd=worktree)
    assert version.code == 0, version.output
    lock = repository.run("uv", "lock", "--check", cwd=worktree)
    assert lock.code == 0, lock.output
    repository.git("add", "--", "pyproject.toml", "uv.lock", cwd=worktree)
    repository.git("commit", "-m", "Start v0.1.1.dev0", "--", "pyproject.toml", "uv.lock", cwd=worktree)
    repository.git("push", "origin", "HEAD:refs/heads/main", cwd=worktree)
    development = repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/heads/main")
    assert repository.git("--git-dir", str(repository.remote), "rev-parse", f"{development}^") == stable


def test_failed_development_push_can_be_recovered_without_changing_release(repository: ReleaseRepository) -> None:
    original = repository.git("rev-parse", "HEAD")
    repository.env["TEST_PUSH_MODE"] = "reject-development"

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert "next-development push failed" in result.output
    stable = assert_remote_at_stable_release(repository)
    area = retained_release_area(result.output)
    assert "Last confirmed state: next-development commit created" in result.output
    line = next(line for line in result.output.splitlines() if line.startswith("Next-development commit: "))
    development = line.removeprefix("Next-development commit: ")
    assert repository.git("rev-parse", f"{development}^") == stable
    assert f"git push origin {development}:refs/heads/main" in result.output
    for name in ("mindful-0.1.0.ankiaddon", "mindful-0.1.0.zip"):
        assert f"GitHub asset {name}: downloaded and matches" in result.output
        assert (Path(repository.env["FAKE_GITHUB"]) / name).read_bytes() == (area / name).read_bytes()

    del repository.env["TEST_PUSH_MODE"]
    repository.git("push", "origin", f"{development}:refs/heads/main")
    assert repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/heads/main") == development
    assert repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/tags/v0.1.0^{}") == stable
    assert repository.git("rev-parse", "HEAD") == original


@pytest.mark.parametrize("diverged", [False, True])
def test_documented_fast_forward_handoff_never_overwrites_caller_history(repository: ReleaseRepository, diverged: bool) -> None:
    result = repository.release("--next-bump", "patch", answer="release")
    assert result.code == 0, result.output
    if diverged:
        (repository.root / "caller.txt").write_text("new local commit", encoding="utf-8")
        repository.git("add", "caller.txt")
        repository.git("commit", "-m", "Unrelated local work")
    local = repository.git("rev-parse", "HEAD")
    repository.git("fetch", "origin", "main")

    handoff = repository.run("git", "merge", "--ff-only", "FETCH_HEAD")

    remote_head = repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/heads/main")
    if diverged:
        assert handoff.code != 0
        assert repository.git("rev-parse", "HEAD") == local
        assert (repository.root / "caller.txt").read_text(encoding="utf-8") == "new local commit"
    else:
        assert handoff.code == 0, handoff.output
        assert repository.git("rev-parse", "HEAD") == remote_head


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("TEST_QUALITY_FAIL", "pytest tests", "test suite failed"),
        ("TEST_QUALITY_FAIL", "ruff check", "Ruff lint failed"),
        ("TEST_QUALITY_FAIL", "ruff format", "Ruff formatting failed"),
        ("TEST_QUALITY_FAIL", "pyrefly check", "Pyrefly failed"),
        ("TEST_QUALITY_FAIL", "lint-imports", "Import architecture checks failed"),
        ("TEST_BUILD_MODE", "fail", "add-on build failed"),
        ("TEST_BUILD_MODE", "invalid", "archive failed validation"),
        ("TEST_UV_UNRELATED", "1", "unrelated edits"),
    ],
)
def test_failing_validation_prevents_tag_and_publication(repository: ReleaseRepository, variable: str, value: str, message: str) -> None:
    original = repository.git("rev-parse", "HEAD")
    repository.env[variable] = value
    repository.env["TEST_CALLER_EDIT"] = str(repository.root / "caller.txt")

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert message in result.output
    assert repository.git("rev-parse", "HEAD") == original
    assert (repository.root / "caller.txt").read_text(encoding="utf-8") == "concurrent caller change"
    assert repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/heads/main") == original
    assert repository.git("tag", "--list", "v0.1.0") == ""
    assert not (Path(repository.env["FAKE_GITHUB"]) / "release-tag").exists()
    assert "Retained worktree" in result.output
    assert len(repository.git("worktree", "list", "--porcelain").split("worktree ")) == 3


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("TEST_ANKI_RUNNING", "1", "extracted installer failed"),
        ("TEST_PLATFORM", "Linux", "Actual macOS installer verification is required"),
    ],
)
def test_installer_verification_failure_blocks_remote_changes(repository: ReleaseRepository, variable: str, value: str, message: str) -> None:
    original = repository.git("rev-parse", "HEAD")
    repository.env[variable] = value

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert message in result.output
    assert repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/heads/main") == original
    assert repository.git("tag", "--list", "v0.1.0") == ""
    assert not (Path(repository.env["FAKE_GITHUB"]) / "release-tag").exists()
    assert "Standalone asset:" in result.output
    assert "Installer asset:" in result.output


@pytest.mark.parametrize("problem", ["layout", "identity", "permissions"])
def test_invalid_bundle_blocks_tag_and_publication(repository: ReleaseRepository, problem: str) -> None:
    real_zip = shutil.which("zip")
    assert real_zip is not None
    repository.env["TEST_REAL_ZIP"] = real_zip
    repository.env["TEST_BUNDLE_PROBLEM"] = problem
    wrapper = Path(repository.env["PATH"].split(os.pathsep)[0]) / "zip"
    wrapper.write_text(
        """#!/bin/sh
if [ "$TEST_BUNDLE_PROBLEM" = identity ]; then
    printf tampered >> "$3/mindful-0.1.0.ankiaddon"
elif [ "$TEST_BUNDLE_PROBLEM" = permissions ]; then
    chmod 644 "$3/install.sh"
fi
"$TEST_REAL_ZIP" "$@" || exit $?
if [ "$TEST_BUNDLE_PROBLEM" = layout ]; then
    echo unexpected > "$3/unexpected"
    "$TEST_REAL_ZIP" -q "$2" "$3/unexpected"
fi
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    original = repository.git("rev-parse", "HEAD")

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert "installer ZIP failed validation" in result.output
    assert repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/heads/main") == original
    assert repository.git("tag", "--list", "v0.1.0") == ""
    assert not (Path(repository.env["FAKE_GITHUB"]) / "release-tag").exists()


@pytest.mark.parametrize("problem", ["identity", "bundled-runtime"])
def test_addon_distribution_contract_failure_blocks_publication(repository: ReleaseRepository, problem: str) -> None:
    if problem == "identity":
        manifest = repository.root / "src" / "mindful" / "manifest.json"
        manifest.write_text('{"package":"other","name":"Other"}', encoding="utf-8")
    else:
        unwanted = repository.root / "src" / "mindful" / "anki" / "__init__.py"
        unwanted.parent.mkdir()
        unwanted.write_text("bundled runtime", encoding="utf-8")
        builder = repository.root / "scripts" / "build_addon.py"
        builder.write_text(
            builder.read_text(encoding="utf-8").replace('    "manifest.json",\n', '    "manifest.json",\n    "anki/__init__.py",\n'),
            encoding="utf-8",
        )
    repository.git("add", "src/mindful", "scripts/build_addon.py")
    repository.git("commit", "-m", "Introduce invalid distribution")
    repository.git("push", "origin", "main")
    original = repository.git("rev-parse", "HEAD")

    result = repository.release("--next-bump", "patch", answer="release")

    assert result.code != 0
    assert "archive failed validation" in result.output
    assert repository.git("--git-dir", str(repository.remote), "rev-parse", "refs/heads/main") == original
    assert repository.git("tag", "--list", "v0.1.0") == ""
    assert not (Path(repository.env["FAKE_GITHUB"]) / "release-tag").exists()
