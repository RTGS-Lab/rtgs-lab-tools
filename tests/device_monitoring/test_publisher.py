import json
from pathlib import Path

import jsonschema
import pytest

from rtgs_lab_tools.device_monitoring import publisher

DM = Path(publisher.__file__).resolve().parent


def sample():
    monitoring = [{"node_id": "e00fce68aaaa", "device_timestamp": "2026-10-14 08:59",
                   "flagged": False, "battery": 4.01, "system": 0.18, "humidity": float("nan"),
                   "errors": [], "is_missing": False, "last_heard": "2026-10-14 08:59:12"}]
    logger_info = [{"node_id": "e00fce68aaaa", "field_name": "WinterTurf_Type_A_64",
                    "product_name": "Winter Turf - v3",
                    "particle_url": "https://console.particle.io/devices/e00fce68aaaa"}]
    config = {"battery_voltage_min": 3.6, "critical_errors": ["SD_ACCESS_FAIL"]}
    return publisher.build_batch(monitoring, logger_info, config, "2026-10-14 09:27",
                                 "2026-10-11", "2026-10-14")


def test_batch_matches_schema_and_id():
    b = sample()
    schema = json.loads((DM / "devmon-batch-1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(b)
    assert b["batch_id"] == publisher.batch_id_of(b)
    assert b["monitoring"][0]["humidity"] is None           # NaN is not JSON


def test_batch_id_is_stable():
    assert sample()["batch_id"] == sample()["batch_id"]


class FakeResponse:
    def __init__(self, code, body):
        self.status_code, self._body, self.text = code, body, json.dumps(body)

    def json(self):
        return self._body


def test_retries_then_succeeds(monkeypatch):
    replies = [FakeResponse(503, {}), FakeResponse(201, {"status": "stored"})]
    monkeypatch.setattr(publisher.requests, "post", lambda *a, **k: replies.pop(0))
    slept = []
    out = publisher.publish(sample(), url="https://x", token="t", sleep=slept.append)
    assert out["status"] == "stored" and slept == [15.0]


def test_bad_request_is_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(publisher.requests, "post",
                        lambda *a, **k: calls.append(1) or FakeResponse(400, {"error": "x"}))
    with pytest.raises(publisher.PublishError):
        publisher.publish(sample(), url="https://x", token="t", sleep=lambda s: None)
    assert len(calls) == 1


def test_needs_url_and_token(monkeypatch):
    monkeypatch.delenv("DEVICEMON_INGEST_URL", raising=False)
    monkeypatch.delenv("DEVICEMON_INGEST_TOKEN", raising=False)
    with pytest.raises(publisher.PublishError):
        publisher.publish(sample())


def test_cron_uses_the_cli_flag_names():
    script = (DM / "scheduled_device_monitoring.sh").read_text()
    for bad in ("--start_date", "--end_date", "--node_ids"):
        assert bad not in script
