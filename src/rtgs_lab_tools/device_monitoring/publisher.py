"""
Overview:
    - Publishes one monitoring run to device-monitoring-ingest (rtgs-infrastructure,
      services/device-monitoring-ingest) instead of writing Cloud SQL directly.
    - Why: GEMS is reachable only from UMN/MSI, so the cron on MSI stays the puller and the
      cloud side only receives. The bearer token is fetched from Secret Manager each run
      (ingest_token.py) and held in memory only; MSI holds a key that can read that one secret.
Payload:
    - devmon-batch/1, defined by devmon-batch-1.schema.json next to this file. It is a copy of
      rtgs-infrastructure services/device-monitoring-ingest/schema/devmon-batch-1.schema.json;
      change both together.
Environment:
    DEVICEMON_INGEST_URL      base URL of the ingest service (deploy run summary)
    DEVICEMON_SA_KEY / DEVICEMON_TOKEN_SECRET   see ingest_token.py (token source)
    DEVICEMON_INGEST_TOKEN    test override only; normally unset (token from Secret Manager)
    DEVICEMON_BATCH_DIR       where each batch is saved before sending
                              (default ~/logs/device-monitoring-batches)
    DEVICEMON_RELEASE         release tag the cron checked out (recorded in the batch)
    DEVICEMON_PUBLISH_ATTEMPTS / DEVICEMON_PUBLISH_BACKOFF   retry policy (5 / 15 s, doubling)
"""

import hashlib
import json
import math
import os
import socket
import subprocess
import time
from pathlib import Path

import requests

from . import ingest_token

SCHEMA_ID = "devmon-batch/1"
SCHEMA_PATH = Path(__file__).resolve().parent / "devmon-batch-1.schema.json"
RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}
REQUEST_TIMEOUT = (10, 60)  # (connect, read) seconds


class PublishError(RuntimeError):
    """The batch was not accepted."""


def canonical(obj):
    """Byte form batch_id is computed over; the ingest service recomputes it the same way."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def batch_id_of(batch):
    body = {k: v for k, v in batch.items() if k != "batch_id"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def _plain(value):
    """numpy/pandas scalars and timestamps -> JSON types; NaN -> None (JSON has no NaN)."""
    if hasattr(value, "item") and not isinstance(value, (list, dict, str)):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _normalize(obj):
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    return _plain(obj)


def _lab_tools_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=Path(__file__).parent,
                              capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def build_batch(monitoring, logger_info, app_config, run_timestamp, start_date, end_date,
                full_fleet=True):
    """Assemble a devmon-batch/1 document from produce_db's record builders."""
    batch = _normalize({
        "schema": SCHEMA_ID,
        "run_timestamp": run_timestamp,
        "window": {"start": start_date, "end": end_date},
        "full_fleet": bool(full_fleet),
        "producer": {"host": socket.gethostname(),
                     "release": os.getenv("DEVICEMON_RELEASE") or "unreleased",
                     "lab_tools_commit": _lab_tools_commit()},
        "monitoring": monitoring,
        "logger_info": logger_info,
        "app_config": app_config,
    })
    batch["batch_id"] = batch_id_of(batch)
    return batch


def save_batch(batch, directory=None):
    """Write the batch where the cron's logs live, before sending: audit copy and replay source."""
    d = Path(directory or os.getenv("DEVICEMON_BATCH_DIR")
             or Path.home() / "logs" / "device-monitoring-batches")
    d.mkdir(parents=True, exist_ok=True)
    stamp = batch["run_timestamp"].replace(" ", "T").replace(":", "")
    data = canonical(batch).encode("utf-8")
    # The batch dir is group-writable on MSI: create the file exclusively and never follow a
    # symlink someone else planted under the expected name.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    for n in range(100):
        path = d / f"{stamp}Z-{batch['batch_id'][:12]}{'' if n == 0 else f'-{n}'}.json"
        try:
            fd = os.open(path, flags, 0o640)
        except FileExistsError:
            continue
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path
    raise PublishError(f"could not create a batch file in {d}")


def publish(batch, url=None, token=None, attempts=None, backoff=None, sleep=time.sleep):
    """POST the batch; retry network errors and 408/425/429/5xx with doubling backoff.

    A 4xx other than those means the batch or token is wrong: retrying unchanged cannot help,
    so it raises at once. Re-sending an already-stored batch returns "duplicate" (no-op).
    """
    url = (url or os.getenv("DEVICEMON_INGEST_URL") or "").rstrip("/")
    if not url:
        raise PublishError("DEVICEMON_INGEST_URL must be set")
    if not token:
        try:
            if not os.getenv("DEVICEMON_INGEST_TOKEN"):
                url = ingest_token.check_ingest_url(url)[0]
            token = ingest_token.load_token(url)
        except ingest_token.TokenError as e:
            raise PublishError(f"no ingest token: {e}") from None
    attempts = int(attempts or os.getenv("DEVICEMON_PUBLISH_ATTEMPTS", "5"))
    backoff = float(backoff or os.getenv("DEVICEMON_PUBLISH_BACKOFF", "15"))
    body = canonical(batch).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
               "Idempotency-Key": batch["batch_id"]}
    last = None
    for attempt in range(1, attempts + 1):
        try:
            r = requests.post(f"{url}/v1/batches", data=body, headers=headers,
                              timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            last = f"{type(e).__name__}: {e}"
        else:
            if r.status_code in (200, 201):
                info = r.json()
                print(f"--Published batch {batch['batch_id'][:12]}: {info.get('status')} "
                      f"({len(batch['monitoring'])} nodes, run {batch['run_timestamp']} UTC)--")
                return info
            if r.status_code not in RETRY_STATUS:
                raise PublishError(f"ingest refused the batch: HTTP {r.status_code} {r.text[:300]}")
            last = f"HTTP {r.status_code} {r.text[:200]}"
        if attempt < attempts:
            delay = min(backoff * 2 ** (attempt - 1), 300)
            print(f"publish attempt {attempt}/{attempts} failed ({last}); retry in {delay:.0f}s")
            sleep(delay)
    raise PublishError(f"publish failed after {attempts} attempts: {last}")


def publish_file(path, **kwargs):
    """Re-send a saved batch (replay, or seeding the test service)."""
    return publish(json.loads(Path(path).read_text()), **kwargs)
