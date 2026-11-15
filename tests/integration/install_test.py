import asyncio
import json
import os
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Result:
    code: int
    output: str


async def execute(args: tuple[str, ...], cwd: Path, env: dict[str, str]) -> Result:
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=30)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise
    return Result(process.returncode or 0, output.decode())


@dataclass
class Installer:
    bundle: Path
    home: Path
    tools: Path
    cwd: Path
    env: dict[str, str]

    @property
    def script(self) -> Path:
        return self.bundle / "install.sh"

    @property
    def archive(self) -> Path:
        return self.bundle / "mindful-0.1.0.ankiaddon"

    @property
    def default_addons(self) -> Path:
        return self.home / "Library" / "Application Support" / "Anki2" / "addons21"

    def run(self, *args: str) -> Result:
        return asyncio.run(execute((str(self.script), *args), self.cwd, self.env))

    def tool(self, name: str, content: str) -> None:
        tool = self.tools / name
        tool.write_text(content, encoding="utf-8")
        tool.chmod(0o755)


@pytest.fixture
def installer(tmp_path: Path) -> Installer:
    root = tmp_path.resolve()
    bundle = root / "release bundle"
    home = root / "home"
    tools = root / "tools"
    checkout = root / "builder checkout"
    for path in (bundle, home, tools, checkout / "scripts"):
        path.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "install.sh", bundle)
    shutil.copy2(ROOT / "scripts" / "build_addon.py", checkout / "scripts")
    shutil.copytree(ROOT / "src" / "mindful", checkout / "src" / "mindful")
    env = os.environ.copy()
    env.update({"HOME": str(home), "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}"})
    result = asyncio.run(execute((sys.executable, str(checkout / "scripts" / "build_addon.py")), root, env))
    assert result.code == 0, result.output
    shutil.copy2(checkout / "dist" / "mindful.ankiaddon", bundle / "mindful-0.1.0.ankiaddon")
    harness = Installer(bundle, home, tools, root, env)
    harness.tool("uname", '#!/bin/sh\nprintf "%s\\n" "${TEST_PLATFORM:-Darwin}"\n')
    harness.tool(
        "ps",
        """#!/bin/sh
case "${TEST_ANKI_STATE:-closed}" in
    closed) echo /usr/bin/other ;;
    running) echo /Applications/Anki.app/Contents/MacOS/Anki ;;
    failed) exit 1 ;;
    empty) exit 0 ;;
esac
""",
    )
    if sys.platform != "darwin":
        harness.tool(
            "plutil",
            f"""#!{sys.executable}
import json, sys
key = sys.argv[sys.argv.index("-extract") + 1]
path = sys.argv[-1]
with (sys.stdin if path == "-" else open(path, encoding="utf-8")) as source:
    print(json.load(source)[key])
""",
        )
        harness.tool(
            "stat",
            f"""#!{sys.executable}
import os, sys
entry = os.stat(sys.argv[-1])
if sys.argv[2] == "%p:%m:%u:%g":
    print(f"{{entry.st_mode:o}}:{{int(entry.st_mtime)}}:{{entry.st_uid}}:{{entry.st_gid}}")
else:
    print(f"{{entry.st_dev}}:{{entry.st_ino}}")
""",
        )
    return harness


def tree(path: Path) -> dict[str, bytes | str | None]:
    if not path.exists():
        return {}
    return {
        child.relative_to(path).as_posix(): (str(child.readlink()) if child.is_symlink() else child.read_bytes() if child.is_file() else None)
        for child in path.rglob("*")
    }


def make_old_installation(addons: Path) -> Path:
    target = addons / "mindful"
    (target / "user_files").mkdir(parents=True)
    (target / "manifest.json").write_text('{"package":"mindful","name":"Mindful"}', encoding="utf-8")
    (target / "__init__.py").write_text("old code", encoding="utf-8")
    (target / "obsolete.py").write_text("obsolete", encoding="utf-8")
    (target / "meta.json").write_text('{"disabled": false}', encoding="utf-8")
    (target / "config.json").write_text('{"option": true}', encoding="utf-8")
    (target / "user_files" / "notes.txt").write_text("preserved", encoding="utf-8")
    return target


def rewrite_archive(archive: Path, *, manifest: bytes | None = None, omit: str = "") -> None:
    with ZipFile(archive) as source:
        entries = [(entry, source.read(entry)) for entry in source.infolist() if entry.filename != omit]
    with ZipFile(archive, "w") as destination:
        for entry, content in entries:
            destination.writestr(entry, manifest if entry.filename == "manifest.json" and manifest is not None else content)


def test_help_works_without_an_installed_anki_folder(installer: Installer) -> None:
    result = installer.run("--help")
    assert result.code == 0
    assert "--addons-dir" in result.output
    assert "--upgrade" in result.output


def test_installs_into_default_folder_without_touching_other_data(installer: Installer) -> None:
    addons = installer.default_addons
    (addons / "another").mkdir(parents=True)
    (addons / "another" / "keep.txt").write_text("other add-on", encoding="utf-8")
    profile = addons.parent / "profile" / "collection.anki2"
    profile.parent.mkdir()
    profile.write_bytes(b"untouched collection")

    result = installer.run()

    assert result.code == 0, result.output
    assert (addons / "mindful" / "__init__.py").read_bytes() == (ROOT / "src" / "mindful" / "__init__.py").read_bytes()
    assert json.loads((addons / "mindful" / "manifest.json").read_text(encoding="utf-8"))["package"] == "mindful"
    assert (addons / "another" / "keep.txt").read_text(encoding="utf-8") == "other add-on"
    assert profile.read_bytes() == b"untouched collection"
    assert "Restart Anki" in result.output
    assert not list(addons.parent.glob(".mindful-install.*"))


def test_installs_into_custom_path_with_spaces_from_another_directory(installer: Installer) -> None:
    addons = installer.cwd / "custom Anki folder" / "addons21"
    addons.mkdir(parents=True)

    result = installer.run("--addons-dir", str(addons))

    assert result.code == 0, result.output
    assert (addons / "mindful" / "bootstrap.py").is_file()
    assert not installer.default_addons.exists()


def test_documented_extracted_bundle_commands_install_and_upgrade(installer: Installer) -> None:
    bundle_zip = installer.cwd / "mindful-0.1.0.zip"
    with ZipFile(bundle_zip, "w") as archive:
        archive.write(installer.script, "mindful-0.1.0/install.sh")
        archive.write(installer.archive, "mindful-0.1.0/mindful-0.1.0.ankiaddon")
    extracted = installer.cwd / "mindful-0.1.0"
    result = asyncio.run(execute(("unzip", "-q", str(bundle_zip)), installer.cwd, installer.env))
    assert result.code == 0, result.output
    assert os.access(extracted / "install.sh", os.X_OK)

    custom = installer.cwd / "custom Anki folder" / "addons21"
    for addons, install_args, upgrade_args in (
        (installer.default_addons, (), ("--upgrade",)),
        (custom, ("--addons-dir", str(custom)), ("--upgrade", "--addons-dir", str(custom))),
    ):
        addons.mkdir(parents=True)
        result = asyncio.run(execute(("./install.sh", *install_args), extracted, installer.env))
        assert result.code == 0, result.output
        (addons / "mindful" / "config.json").write_text('{"keep": true}', encoding="utf-8")
        result = asyncio.run(execute(("./install.sh", *upgrade_args), extracted, installer.env))
        assert result.code == 0, result.output
        assert (addons / "mindful" / "config.json").read_text(encoding="utf-8") == '{"keep": true}'
        assert len(list((addons.parent / "mindful-backups").glob("*/mindful"))) == 1


@pytest.mark.skipif(sys.platform != "darwin", reason="Requires macOS system tools")
def test_extracted_installer_runs_with_actual_macos_system_tools(installer: Installer) -> None:
    process_check = asyncio.run(execute(("/bin/ps", "-axo", "comm="), installer.cwd, installer.env))
    if process_check.code != 0 or any(Path(line.strip()).name.lower() == "anki" for line in process_check.output.splitlines()):
        pytest.skip("Anki is running or its process state cannot be inspected")
    (installer.tools / "uname").unlink()
    (installer.tools / "ps").unlink()
    bundle_zip = installer.cwd / "mindful-0.1.0.zip"
    with ZipFile(bundle_zip, "w") as archive:
        archive.write(installer.script, "mindful-0.1.0/install.sh")
        archive.write(installer.archive, "mindful-0.1.0/mindful-0.1.0.ankiaddon")
    result = asyncio.run(execute(("/usr/bin/unzip", "-q", str(bundle_zip)), installer.cwd, installer.env))
    assert result.code == 0, result.output
    addons = installer.cwd / "real macOS tools" / "addons21"
    addons.mkdir(parents=True)

    result = asyncio.run(execute(("./install.sh", "--addons-dir", str(addons)), installer.cwd / "mindful-0.1.0", installer.env))

    assert result.code == 0, result.output
    assert (addons / "mindful" / "__init__.py").read_bytes() == (ROOT / "src" / "mindful" / "__init__.py").read_bytes()


@pytest.mark.parametrize("destination", ["missing", "relative", "unwritable"])
def test_unusable_destination_is_rejected_without_installing(installer: Installer, destination: str) -> None:
    addons = installer.cwd / "Anki" / "addons21"
    if destination == "unwritable":
        addons.mkdir(parents=True)
        addons.chmod(0o500)
        if os.access(addons, os.W_OK):
            pytest.skip("Current user can write to the permission-restricted directory")
    path = "relative/addons21" if destination == "relative" else str(addons)
    try:
        result = installer.run("--addons-dir", path)
    finally:
        if addons.exists():
            addons.chmod(0o700)

    assert result.code != 0
    assert not (addons / "mindful").exists()


def test_unsupported_platform_directs_user_to_standalone_archive(installer: Installer) -> None:
    installer.env["TEST_PLATFORM"] = "Linux"
    addons = installer.cwd / "addons21"
    addons.mkdir()

    result = installer.run("--addons-dir", str(addons))

    assert result.code != 0
    assert "standalone .ankiaddon" in result.output
    assert tree(addons) == {}


@pytest.mark.parametrize(
    "problem",
    [
        "missing",
        "multiple",
        "corrupt",
        "traversal",
        "absolute",
        "backslash",
        "newline",
        "duplicate",
        "case-duplicate",
        "symlink",
        "reserved",
        "reserved-meta",
        "reserved-config",
        "identity",
        "entrypoint",
    ],
)
def test_invalid_archive_cannot_change_existing_installation(installer: Installer, problem: str) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)
    if problem == "missing":
        installer.archive.unlink()
    elif problem == "multiple":
        shutil.copy2(installer.archive, installer.bundle / "mindful-0.2.0.ankiaddon")
    elif problem == "corrupt":
        installer.archive.write_bytes(b"not an archive")
    elif problem in {"identity", "entrypoint"}:
        rewrite_archive(
            installer.archive,
            manifest=b'{"package":"other","name":"Other"}' if problem == "identity" else None,
            omit="__init__.py" if problem == "entrypoint" else "",
        )
    else:
        with ZipFile(installer.archive, "a") as archive:
            if problem == "symlink":
                link = ZipInfo("linked.py")
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(link, "../outside")
            elif problem == "duplicate":
                with pytest.warns(UserWarning, match="Duplicate name"):
                    archive.writestr("manifest.json", '{"package":"mindful"}')
            else:
                name = {
                    "traversal": "../escape.py",
                    "absolute": "/escape.py",
                    "backslash": "directory\\escape.py",
                    "newline": "directory\nescape.py",
                    "case-duplicate": "Manifest.json",
                    "reserved": "user_files/overwrite.txt",
                    "reserved-meta": "meta.json",
                    "reserved-config": "config.json",
                }[problem]
                archive.writestr(name, "unsafe")

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0, result.output
    assert tree(target) == before
    assert not (addons.parent / "mindful-backups").exists()
    assert not list(addons.parent.glob(".mindful-install.*"))


@pytest.mark.parametrize("state", ["running", "failed", "empty"])
def test_running_or_uninspectable_anki_stops_before_changes(installer: Installer, state: str) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)
    installer.env["TEST_ANKI_STATE"] = state

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    assert tree(target) == before
    assert not (addons.parent / "mindful-backups").exists()


def test_large_process_listing_does_not_delay_installation(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    addons.mkdir(parents=True)
    installer.tool("ps", f"#!{sys.executable}\nprint(' ' * 200_000 + 'other-process')\n")

    result = installer.run("--addons-dir", str(addons))

    assert result.code == 0, result.output
    assert (addons / "mindful" / "__init__.py").is_file()


def test_symlinked_destination_and_development_target_are_rejected(installer: Installer) -> None:
    real = installer.cwd / "real"
    real.mkdir()
    link = installer.cwd / "linked"
    link.symlink_to(real, target_is_directory=True)
    (real / "addons21").mkdir()

    result = installer.run("--addons-dir", str(link / "addons21"))

    assert result.code != 0
    assert tree(real / "addons21") == {}
    target = real / "addons21" / "mindful"
    target.symlink_to(installer.cwd / "source", target_is_directory=True)
    result = installer.run("--addons-dir", str(real / "addons21"), "--upgrade")
    assert result.code != 0
    assert target.is_symlink()


@pytest.mark.parametrize("symlinked", [False, True])
def test_conflicting_mindful_copy_is_not_overwritten(installer: Installer, symlinked: bool) -> None:
    addons = installer.cwd / "data" / "addons21"
    other = installer.cwd / "other source" if symlinked else addons / "123456789"
    other.mkdir(parents=True)
    if symlinked:
        addons.mkdir(parents=True)
        (addons / "123456789").symlink_to(other, target_is_directory=True)
    (other / "manifest.json").write_text('{"package":"mindful"}', encoding="utf-8")
    before = tree(other)

    result = installer.run("--addons-dir", str(addons))

    assert result.code != 0
    assert tree(other) == before
    assert not (addons / "mindful").exists()


def test_existing_installation_requires_explicit_upgrade(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)

    result = installer.run("--addons-dir", str(addons))

    assert result.code != 0
    assert "--upgrade" in result.output
    assert tree(target) == before
    assert not (addons.parent / "mindful-backups").exists()


def test_upgrade_preserves_user_files_and_retains_complete_backup(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    (target / "config.json").chmod(0o600)
    (target / "user_files").chmod(0o700)
    modes = {path: stat.S_IMODE((target / path).stat().st_mode) for path in ("config.json", "user_files")}
    before = tree(target)
    (addons / "another").mkdir()
    (addons / "another" / "keep").write_text("other", encoding="utf-8")

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code == 0, result.output
    assert (target / "__init__.py").read_bytes() == (ROOT / "src" / "mindful" / "__init__.py").read_bytes()
    assert not (target / "obsolete.py").exists()
    for path in ("meta.json", "config.json", "user_files/notes.txt"):
        assert (target / path).read_bytes() == before[path]
    backups = list((addons.parent / "mindful-backups").glob("*/mindful"))
    assert len(backups) == 1
    assert tree(backups[0]) == before
    for path, mode in modes.items():
        assert stat.S_IMODE((target / path).stat().st_mode) == mode
        assert stat.S_IMODE((backups[0] / path).stat().st_mode) == mode
    assert str(backups[0]) in result.output
    assert (addons / "another" / "keep").read_text(encoding="utf-8") == "other"


def test_upgrade_rejects_symlinked_user_data(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    external = installer.cwd / "external"
    external.write_text("external", encoding="utf-8")
    (target / "user_files" / "link").symlink_to(external)
    before = tree(target)

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    assert tree(target) == before
    assert external.read_text(encoding="utf-8") == "external"
    assert not (addons.parent / "mindful-backups").exists()


def test_failed_copy_retains_backup_and_reports_recovery(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)
    installer.tool(
        "cp",
        """#!/bin/sh
if [ "$1" = "-pRn" ]; then exit 1; fi
exec /bin/cp "$@"
""",
    )

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    backups = list((addons.parent / "mindful-backups").glob("*/mindful"))
    assert len(backups) == 1
    assert tree(backups[0]) == before
    assert f"Verified backup: {backups[0]}" in result.output
    assert "Restore from the verified backup" in result.output


def test_failed_backup_is_reported_as_incomplete_without_changing_original(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)
    installer.env["TEST_TARGET"] = str(target)
    installer.tool(
        "cp",
        """#!/bin/sh
if [ "$1" = "-pR" ] && [ "$2" = "$TEST_TARGET" ]; then
    /bin/mkdir "$3"
    printf partial > "$3/partial"
    exit 1
fi
exec /bin/cp "$@"
""",
    )

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    assert tree(target) == before
    backups = list((addons.parent / "mindful-backups").glob("*/mindful"))
    assert len(backups) == 1
    assert (backups[0] / "partial").read_text(encoding="utf-8") == "partial"
    assert "Incomplete backup (do not restore)" in result.output
    assert "Verified backup:" not in result.output


def test_new_anki_process_stops_upgrade_before_replacement(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)
    installer.env["TEST_PROCESS_COUNTER"] = str(installer.cwd / "ps-checked")
    installer.tool(
        "ps",
        """#!/bin/sh
if [ -e "$TEST_PROCESS_COUNTER" ]; then
    echo /Applications/Anki.app/Contents/MacOS/Anki
else
    : > "$TEST_PROCESS_COUNTER"
    echo /usr/bin/other
fi
""",
    )

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    assert tree(target) == before
    backups = list((addons.parent / "mindful-backups").glob("*/mindful"))
    assert len(backups) == 1
    assert tree(backups[0]) == before
    assert "Anki is running" in result.output


def test_concurrent_old_installation_change_is_retained_for_recovery(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)
    installer.env["TEST_TARGET"] = str(target)
    installer.tool(
        "mv",
        """#!/bin/sh
if [ "$1" = "$TEST_TARGET" ]; then
    printf 'newer change' > "$1/user_files/notes.txt"
fi
exec /bin/mv "$@"
""",
    )

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    backups = list((addons.parent / "mindful-backups").glob("*/mindful"))
    staging = list(addons.parent.glob(".mindful-install.*/previous/mindful"))
    assert len(backups) == len(staging) == 1
    assert tree(backups[0]) == before
    assert (staging[0] / "user_files" / "notes.txt").read_text(encoding="utf-8") == "newer change"
    assert str(staging[0]) in result.output
    assert "possibly containing newer changes" in result.output


def test_concurrent_target_creation_is_not_overwritten(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)
    installer.env["TEST_TARGET"] = str(target)
    installer.tool(
        "mkdir",
        """#!/bin/sh
if [ "$1" = "$TEST_TARGET" ]; then
    /bin/mkdir "$1"
    echo concurrent > "$1/concurrent.txt"
    exit 1
fi
exec /bin/mkdir "$@"
""",
    )

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    assert tree(target) == {"concurrent.txt": b"concurrent\n"}
    backups = list((addons.parent / "mindful-backups").glob("*/mindful"))
    assert len(backups) == 1
    assert tree(backups[0]) == before
    assert "Do not overwrite" in result.output


def test_concurrent_file_is_not_overwritten_during_copy(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    before = tree(target)
    installer.tool(
        "cp",
        """#!/bin/sh
if [ "$1" = "-pRn" ]; then
    printf 'concurrent content' > ./__init__.py
fi
exec /bin/cp "$@"
""",
    )

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    assert (target / "__init__.py").read_text(encoding="utf-8") == "concurrent content"
    backups = list((addons.parent / "mindful-backups").glob("*/mindful"))
    assert len(backups) == 1
    assert tree(backups[0]) == before
    assert "Do not overwrite" in result.output


def test_target_swapped_for_symlink_does_not_write_outside_addons(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    target = make_old_installation(addons)
    external = installer.cwd / "external"
    external.mkdir()
    moved = addons / "moved-by-other-process"
    installer.env.update({"TEST_TARGET": str(target), "TEST_EXTERNAL": str(external), "TEST_MOVED": str(moved)})
    installer.tool(
        "cp",
        """#!/bin/sh
if [ "$1" = "-pRn" ]; then
    /bin/mv "$TEST_TARGET" "$TEST_MOVED"
    /bin/ln -s "$TEST_EXTERNAL" "$TEST_TARGET"
fi
exec /bin/cp "$@"
""",
    )

    result = installer.run("--addons-dir", str(addons), "--upgrade")

    assert result.code != 0
    assert target.is_symlink()
    assert tree(external) == {}
    assert (moved / "__init__.py").is_file()
    assert "destination changed" in result.output


def test_failed_fresh_install_does_not_claim_a_backup_exists(installer: Installer) -> None:
    addons = installer.cwd / "data" / "addons21"
    addons.mkdir(parents=True)
    installer.tool("cp", '#!/bin/sh\n[ "$1" != "-pRn" ] || exit 1\nexec /bin/cp "$@"\n')

    result = installer.run("--addons-dir", str(addons))

    assert result.code != 0
    assert "inspect" in result.output
    assert "backup" not in result.output.lower()
    assert list(addons.parent.glob(".mindful-install.*"))
