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


def run(ws, release=None):
    if release is not None:
        f = ws["home"] / ".config/devmon/release"
        f.write_text(release)
        os.chmod(f, 0o600)
    env = {"HOME": str(ws["home"]), "PATH": os.environ["PATH"],
           "DEVICEMON_BASE_DIR": str(ws["base"]), "DEVICEMON_INGEST_TOKEN": "must-be-unset"}
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
    assert "Virtual environment not found after installation" in r.stdout
    assert not (ws["tmp"] / "hook-ran").exists()
    logs = list((ws["base"] / "logs").glob("device_monitoring_*.log"))
    assert len(logs) == 1 and len(logs[0].name.split("_")[-1]) == len("XXXXXX.log")
    assert (logs[0].stat().st_mode & 0o777) == 0o640
    assert (ws["home"] / ".cache/devmon/device_monitoring.lock").exists()
