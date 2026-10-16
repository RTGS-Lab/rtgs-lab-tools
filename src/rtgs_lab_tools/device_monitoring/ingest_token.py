"""
Overview:
    - Fetches the device-monitoring-ingest bearer token from Google Secret Manager at run time,
      so rotating the token never touches MSI. The token lives only in this process's memory:
      it is never logged, printed, written to a batch file, or passed on a command line.
Credentials:
    - A service-account JSON key owned by the running user, mode 600 (or 400):
      DEVICEMON_SA_KEY (default ~/.config/devmon/sa.json). The account
      (device-monitoring-msi@rtgslab) can read the two token secrets and nothing else.
    - The key is used explicitly; GOOGLE_APPLICATION_CREDENTIALS is never set, so nothing else
      in rtgs-lab-tools picks it up as Application Default Credentials.
Environment:
    DEVICEMON_SA_KEY          service-account key file (default ~/.config/devmon/sa.json)
    DEVICEMON_TOKEN_SECRET    secret name; default follows DEVICEMON_INGEST_URL:
                              the test service -> devicemon-ingest-token-test,
                              otherwise devicemon-ingest-token
    DEVICEMON_GCP_PROJECT     project holding the secret (default rtgslab)
    DEVICEMON_INGEST_TOKEN    explicit override for tests only; the MSI cron unsets it
"""

import base64
import json
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import urlparse

SM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
SM_URL = "https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{secret}/versions/latest:access"
DEFAULT_PROJECT = "rtgslab"
DEFAULT_KEY = "~/.config/devmon/sa.json"
PROD_SECRET = "devicemon-ingest-token"
TEST_SECRET = "devicemon-ingest-token-test"
REQUEST_TIMEOUT = (10, 30)

# The only hosts the bearer token is ever sent to, and the secret each one accepts. A URL from
# the group-writable credentials file cannot redirect the token anywhere else.
INGEST_HOSTS = {
    "device-monitoring-ingest-prod-685278787484.us-central1.run.app": PROD_SECRET,
    "device-monitoring-ingest-prod-ieix5g464a-uc.a.run.app": PROD_SECRET,
    "device-monitoring-ingest-test-685278787484.us-central1.run.app": TEST_SECRET,
}
_SECRET_NAME = re.compile(r"^[A-Za-z0-9_-]{1,255}$")


class TokenError(RuntimeError):
    """The ingest token could not be obtained. The message never contains a secret.

    transient=True: a network or server-side failure worth retrying later; False: setup is
    wrong (key file, IAM, names) and retrying unchanged cannot help.
    """

    def __init__(self, message, transient=False):
        super().__init__(message)
        self.transient = transient


def check_ingest_url(url):
    """Return (base_url, secret_for_host); refuse anything but https to a known ingest host."""
    u = urlparse((url or "").strip())
    if u.scheme != "https" or u.hostname not in INGEST_HOSTS or u.port not in (None, 443):
        raise TokenError(f"refusing to send the ingest token to {url!r}: not one of the known "
                         f"device-monitoring-ingest hosts (https only): "
                         f"{', '.join(sorted(INGEST_HOSTS))}")
    return f"https://{u.hostname}", INGEST_HOSTS[u.hostname]


def secret_for(url=None, env=None):
    """Secret name for this run: DEVICEMON_TOKEN_SECRET, else the one the URL's host accepts."""
    env = os.environ if env is None else env
    host_secret = check_ingest_url(url)[1] if url else None
    name = (env.get("DEVICEMON_TOKEN_SECRET") or host_secret or PROD_SECRET).strip()
    if not _SECRET_NAME.match(name):
        raise TokenError(f"DEVICEMON_TOKEN_SECRET {name!r} is not a valid secret name")
    if host_secret and name != host_secret:
        raise TokenError(f"secret {name} does not belong to {url}; that host takes {host_secret}")
    return name


def read_key_file(path):
    """Load the service-account key, failing closed unless it is ours, a regular file, and 600."""
    p = Path(os.path.expanduser(path))
    try:
        fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        raise TokenError(f"service-account key {p} not found. Copy it from the machine that ran "
                         f"devmon-msi-sa-setup.sh, then chmod 600 it") from None
    except OSError as e:
        raise TokenError(f"cannot open service-account key {p}: {e.strerror} "
                         f"(a symlink is refused)") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise TokenError(f"service-account key {p} is not a regular file")
        if st.st_uid != os.geteuid():
            raise TokenError(f"service-account key {p} is owned by uid {st.st_uid}, not by the "
                             f"running user (uid {os.geteuid()}); refusing it")
        mode = stat.S_IMODE(st.st_mode)
        if mode not in (0o600, 0o400):
            raise TokenError(f"service-account key {p} has mode {mode:03o}; it must be 600 "
                             f"(run: chmod 600 {p})")
        with os.fdopen(fd, "rb") as f:
            fd = None
            raw = f.read(65536)
    finally:
        if fd is not None:
            os.close(fd)
    try:
        info = json.loads(raw)
    except ValueError:
        raise TokenError(f"service-account key {p} is not valid JSON") from None
    if not isinstance(info, dict) or info.get("type") != "service_account":
        raise TokenError(f"{p} is not a service-account key (type != service_account)")
    return info


def _session(info):
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_info(info, scopes=[SM_SCOPE])
    return AuthorizedSession(creds)


def fetch_from_secret_manager(secret, key_path=None, project=None, session_factory=_session):
    """Return (token, version_name). version_name ('.../versions/3') is safe to log."""
    key_path = key_path or os.getenv("DEVICEMON_SA_KEY") or DEFAULT_KEY
    project = project or os.getenv("DEVICEMON_GCP_PROJECT") or DEFAULT_PROJECT
    if not _SECRET_NAME.match(secret) or not _SECRET_NAME.match(project):
        raise TokenError("invalid secret or project name")
    info = read_key_file(key_path)
    url = SM_URL.format(project=project, secret=secret)
    try:
        r = session_factory(info).get(url, timeout=REQUEST_TIMEOUT)
    except Exception as e:  # auth refresh or network; neither message carries the secret
        raise TokenError(f"Secret Manager request for {secret} failed: {type(e).__name__}: "
                         f"{str(e)[:200]}", transient=True) from None
    if r.status_code != 200:
        try:
            err = r.json().get("error", {})
            why = f"{err.get('status', '')} {err.get('message', '')[:200]}".strip()
        except Exception:
            why = ""
        hint = {403: "the service account cannot read this secret (IAM)",
                404: "no such secret, or no enabled version",
                400: "latest version is disabled or destroyed"}.get(r.status_code, "")
        raise TokenError(f"Secret Manager refused {project}/{secret}: HTTP {r.status_code} "
                         f"{why} {('-- ' + hint) if hint else ''}".rstrip(),
                         transient=r.status_code == 429 or r.status_code >= 500)
    body = r.json()
    try:
        token = base64.b64decode(body["payload"]["data"]).decode("utf-8").strip()
    except Exception:
        raise TokenError(f"Secret Manager returned no usable payload for {secret}") from None
    if not token:
        raise TokenError(f"secret {secret} is empty")
    return token, body.get("name", f"projects/{project}/secrets/{secret}/versions/?")


def load_token(url=None, env=None, fetch=fetch_from_secret_manager):
    """The bearer token for this run. DEVICEMON_INGEST_TOKEN wins, for tests only."""
    env = os.environ if env is None else env
    override = env.get("DEVICEMON_INGEST_TOKEN")
    if override:
        print("WARNING: using DEVICEMON_INGEST_TOKEN from the environment (test override), "
              "not Secret Manager", file=sys.stderr)
        return override.strip()
    token, _version = fetch(secret_for(url, env))
    return token
