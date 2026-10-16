"""The MSI cron script: credentials parsing and the refuse-to-run checks."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from rtgs_lab_tools.device_monitoring import publisher

SCRIPT = Path(publisher.__file__).resolve().parent / "scheduled_device_monitoring.sh"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}


def check_creds(tmp_path, text):
    f = tmp_path / "creds"
    f.write_text(text)
    out = subprocess.run(["bash", str(SCRIPT), "--check-creds", str(f)], capture_output=True,
                         text=True, check=True, cwd=tmp_path).stdout
    return out.split("\n")


def test_parser_allowlist(tmp_path):
    marker = tmp_path / "pwned"
    lines = check_creds(tmp_path, f"""# comment
export DEVICEMON_INGEST_URL="https://device-monitoring-ingest-test-685278787484.us-central1.run.app"
DB_HOST=gems.example.org   # trailing comment
DB_PASSWORD='pa ss$(touch {marker})'
PARTICLE_ACCESS_TOKEN=abc$(touch {marker})
PATH=/tmp/evil
LD_PRELOAD=/tmp/evil.so
PYTHONPATH=/tmp/evil
DEVICEMON_WORK_DIR=/tmp/evil
DEVICEMON_RELEASE=devmon-v9
DEVICEMON_INGEST_TOKEN=leaked
GOOGLE_APPLICATION_CREDENTIALS=/tmp/k.json
SOMETHING_ELSE=1
$(touch {marker})
""")
    assert not marker.exists()                       # nothing was executed
    url = "https://device-monitoring-ingest-test-685278787484.us-central1.run.app"
    assert f"accepted DEVICEMON_INGEST_URL len={len(url)}" in lines
    assert f"accepted DB_HOST len={len('gems.example.org')}" in lines
    assert f"accepted DB_PASSWORD len={len('pa ss$(touch ' + str(marker) + ')')}" in lines
    assert any(l.startswith("accepted PARTICLE_ACCESS_TOKEN") for l in lines)
    rejected = " ".join(l for l in lines if l.startswith("rejected"))
    for name in ("PATH", "LD_PRELOAD", "PYTHONPATH", "DEVICEMON_WORK_DIR", "DEVICEMON_RELEASE",
                 "DEVICEMON_INGEST_TOKEN", "GOOGLE_APPLICATION_CREDENTIALS", "SOMETHING_ELSE"):
        assert f"rejected {name}(" in rejected
    assert "not-KEY=VALUE" in rejected
    assert "leaked" not in "".join(lines) and "pa ss" not in "".join(lines)


def test_no_set_x_or_source_of_creds():
    text = SCRIPT.read_text()
    assert "set -x" not in text and "bash -x" not in text
    assert 'source "$f"' not in text and "fetch --tags --force" not in text
    assert "core.hooksPath=/dev/null" in text


@pytest.fixture
def ws(tmp_path):
    """A fake shared workspace + home; the script copy is ours and 750."""
    home, base = tmp_path / "home", tmp_path / "shared"
    (home / ".config/devmon").mkdir(parents=True)
    (base / "scripts").mkdir(parents=True)
    (base / "credentials").mkdir()
    (base / "logs").mkdir()
    os.chmod(base / "logs", 0o2770)
    script = base / "scripts/scheduled_device_monitoring.sh"
    shutil.copy(SCRIPT, script)
    os.chmod(script, 0o750)
    os.chmod(base / "scripts", 0o2750)
    (base / "credentials/.rtgs_credentials").write_text(
        "DEVICEMON_INGEST_URL=https://device-monitoring-ingest-test-685278787484"
        ".us-central1.run.app\n")
    # a pinned "release": a local repo with one tagged commit and a hook that must never run
    repo = base / "rtgs-lab-tools-cron/rtgs-lab-tools"
    repo.mkdir(parents=True)
    env = {**os.environ, **GIT_ENV}
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=env)
    (repo / "install.sh").write_text("exit 0\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "r"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "tag", "devmon-v0.0.1"], check=True, env=env)
    hook = repo / ".git/hooks/post-checkout"
    hook.write_text(f"#!/bin/sh\ntouch {tmp_path}/hook-ran\n")
    os.chmod(hook, 0o750)
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                         text=True, check=True).stdout.strip()
    subprocess.run(["chmod", "-R", "g-w,o-w", str(base / "rtgs-lab-tools-cron")], check=True)
    os.chmod(base / "rtgs-lab-tools-cron", 0o2750)
    return {"home": home, "base": base, "script": script, "sha": sha, "tmp": tmp_path}


def run(ws, release=None, **extra_env):
    if release is not None:
        f = ws["home"] / ".config/devmon/release"
        f.write_text(release)
        os.chmod(f, 0o600)
    env = {"HOME": str(ws["home"]), "PATH": os.environ["PATH"],
           "DEVICEMON_BASE_DIR": str(ws["base"]), "DEVICEMON_INGEST_TOKEN": "must-be-unset",
           **extra_env}
    return subprocess.run(["bash", str(ws["script"])], capture_output=True, text=True, env=env,
                          cwd=ws["tmp"], timeout=60)


def test_refuses_group_writable_script(ws):
    os.chmod(ws["script"], 0o770)
    r = run(ws, f"devmon-v0.0.1 {ws['sha']}\n")
    assert r.returncode == 1 and "group/world-writable" in r.stdout


def test_refuses_group_writable_repo(ws):
    os.chmod(ws["base"] / "rtgs-lab-tools-cron/rtgs-lab-tools", 0o2770)
    r = run(ws, f"devmon-v0.0.1 {ws['sha']}\n")
    assert r.returncode == 1 and "group/world-writable" in r.stdout


def test_refuses_missing_or_bad_release_pin(ws):
    assert "release pin" in run(ws).stdout
    assert "must hold one line" in run(ws, "devmon-v0.0.1\n").stdout
    r = run(ws, "devmon-v0.0.1 " + "0" * 40 + "\n")
    assert r.returncode == 1 and "the pin says" in r.stdout


def test_pinned_release_checks_out_without_hooks(ws):
    r = run(ws, f"devmon-v0.0.1 {ws['sha']}\n")
    # gets past the pin and stops at the (fake) venv, having run no repository hook
    assert f"devmon-v0.0.1 ({ws['sha']})" in r.stdout
    assert "requirements-cron.txt is not in release devmon-v0.0.1" in r.stdout
    assert not (ws["tmp"] / "hook-ran").exists()
    logs = list((ws["base"] / "logs").glob("device_monitoring_*.log"))
    assert len(logs) == 1 and len(logs[0].name.split("_")[-1]) == len("XXXXXX.log")
    assert (logs[0].stat().st_mode & 0o777) == 0o640
    assert (ws["home"] / ".cache/devmon/device_monitoring.lock").exists()


# A stand-in interpreter: logs every call, answers the version probes, and makes a "venv" whose
# python is itself. Lets the tests follow the install and run commands without pip or a network.
STUB_PY = """#!/bin/bash
echo "$0 $*" >> "$STUB_LOG"
case "$1" in
  -c) case "$2" in *print*) echo "${STUB_VERSION:-3.12.4}" ;;
                   *) [ "${STUB_VERSION:-3.12.4}" != 3.6.8 ] ;; esac ;;
  -m) [ "$2" = venv ] && mkdir -p "$3/bin" && cp "$0" "$3/bin/python"; exit 0 ;;
esac
"""


def stub_python(ws):
    py = ws["tmp"] / "stubpy"
    py.write_text(STUB_PY)
    os.chmod(py, 0o750)
    return py


def release_with_requirements(ws):
    """Tag devmon-v0.0.2: the fake release plus a requirements-cron.txt."""
    repo = ws["base"] / "rtgs-lab-tools-cron/rtgs-lab-tools"
    env = {**os.environ, **GIT_ENV}
    os.chmod(repo, 0o750)
    reqs = repo / "src/rtgs_lab_tools/device_monitoring/requirements-cron.txt"
    reqs.parent.mkdir(parents=True)
    reqs.write_text("click==8.2.1\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "r2"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "tag", "devmon-v0.0.2"], check=True, env=env)
    subprocess.run(["chmod", "-R", "g-w,o-w", str(repo)], check=True)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def test_refuses_python_older_than_310(ws):
    sha = release_with_requirements(ws)
    log = ws["tmp"] / "py.log"
    r = run(ws, f"devmon-v0.0.2 {sha}\n", DEVICEMON_PYTHON=str(stub_python(ws)),
            STUB_LOG=str(log), STUB_VERSION="3.6.8")
    assert r.returncode == 1 and "is Python 3.6.8; need >= 3.10" in r.stdout
    assert "-m venv" not in log.read_text()
    assert not (ws["base"] / "rtgs-lab-tools-cron/rtgs-lab-tools/venv").exists()


def test_builds_lean_venv_and_runs_the_devmon_cli(ws):
    sha = release_with_requirements(ws)
    log = ws["tmp"] / "py.log"
    r = run(ws, f"devmon-v0.0.2 {sha}\n", DEVICEMON_PYTHON=str(stub_python(ws)),
            STUB_LOG=str(log))
    assert r.returncode == 0, r.stdout + r.stderr
    calls = [c.split(" ", 1)[1] for c in log.read_text().splitlines()]
    pip = [c for c in calls if c.startswith("-m pip")]
    assert len(pip) == 2
    assert pip[0].endswith("-r src/rtgs_lab_tools/device_monitoring/requirements-cron.txt")
    assert pip[1].endswith("--no-deps -e .")
    assert "-m venv venv" in calls
    runs = [c for c in calls if c.startswith("-m rtgs_lab_tools.device_monitoring.cli")]
    assert runs[0].endswith("check-ingest") and runs[1].startswith(
        "-m rtgs_lab_tools.device_monitoring.cli monitor")
    venv = ws["base"] / "rtgs-lab-tools-cron/rtgs-lab-tools/venv"
    bad = subprocess.run(["find", str(venv), "-perm", "/022"], capture_output=True,
                         text=True).stdout
    assert bad == ""                                  # umask 027: group may read, never write
    assert (venv / ".devmon-installed-release").read_text().strip() == f"devmon-v0.0.2 {sha}"
    # the next run of the same release installs nothing
    log.write_text("")
    r = run(ws, f"devmon-v0.0.2 {sha}\n", DEVICEMON_PYTHON=str(stub_python(ws)),
            STUB_LOG=str(log))
    assert r.returncode == 0 and "-m pip" not in log.read_text()


def test_never_runs_install_sh_or_full_extras():
    text = SCRIPT.read_text()
    assert "bash install.sh" not in text and "[dev]" not in text and "[all]" not in text
    assert "pip install --quiet -e ." not in text     # the full base dependencies
