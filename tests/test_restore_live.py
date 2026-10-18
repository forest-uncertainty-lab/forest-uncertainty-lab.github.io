import subprocess

from sulteng.config import ROOT

SCRIPT = ROOT / "scripts" / "restore_live.sh"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "init.defaultBranch=main"]


def git(cwd, *args):
    subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True)


def clone(tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(remote))
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(remote), str(work))
    return work


def restore(work):
    return subprocess.run(["bash", str(SCRIPT), "data/live"], cwd=work, capture_output=True, text=True)


def test_missing_branch_starts_empty(tmp_path):
    work = clone(tmp_path)
    result = restore(work)
    assert result.returncode == 0, result.stderr
    assert (work / "data" / "live").is_dir() and not any((work / "data" / "live").iterdir())


def test_existing_branch_is_restored(tmp_path):
    work = clone(tmp_path)
    git(work, "checkout", "-q", "--orphan", "data-store")
    (work / "now.json").write_text("{}")
    git(work, "add", "now.json")
    git(work, "commit", "-q", "-m", "live")
    git(work, "push", "-q", "origin", "data-store")
    git(work, "checkout", "-q", "--orphan", "other")
    git(work, "rm", "-q", "-rf", "--cached", ".")
    (work / "now.json").unlink()
    result = restore(work)
    assert result.returncode == 0, result.stderr
    assert (work / "data" / "live" / "now.json").read_text() == "{}"


def test_unreachable_remote_stops_the_run(tmp_path):
    work = clone(tmp_path)
    git(work, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    result = restore(work)
    assert result.returncode != 0
    assert "stopping" in result.stderr
