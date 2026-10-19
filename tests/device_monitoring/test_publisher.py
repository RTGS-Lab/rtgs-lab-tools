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


def test_needs_url(monkeypatch):
    monkeypatch.delenv("DEVICEMON_INGEST_URL", raising=False)
    monkeypatch.delenv("DEVICEMON_INGEST_TOKEN", raising=False)
    with pytest.raises(publisher.PublishError, match="DEVICEMON_INGEST_URL"):
        publisher.publish(sample())


def test_no_token_source_fails_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("DEVICEMON_INGEST_TOKEN", raising=False)
    monkeypatch.setenv("DEVICEMON_SA_KEY", str(tmp_path / "missing.json"))
    monkeypatch.setattr(publisher.requests, "post", lambda *a, **k: pytest.fail("posted"))
    with pytest.raises(publisher.PublishError, match="not found"):
        publisher.publish(sample(), url="https://device-monitoring-ingest-test-685278787484"
                                        ".us-central1.run.app")


def test_token_never_sent_to_unknown_host(monkeypatch):
    monkeypatch.delenv("DEVICEMON_INGEST_TOKEN", raising=False)
    monkeypatch.setattr(publisher.requests, "post", lambda *a, **k: pytest.fail("posted"))
    with pytest.raises(publisher.PublishError, match="refusing"):
        publisher.publish(sample(), url="https://evil.example.run.app")


def test_save_batch_is_exclusive_and_ignores_planted_symlink(tmp_path):
    b = sample()
    target = tmp_path / "victim"
    target.write_text("keep")
    stamp = b["run_timestamp"].replace(" ", "T").replace(":", "")
    (tmp_path / f"{stamp}Z-{b['batch_id'][:12]}.json").symlink_to(target)
    p = publisher.save_batch(b, tmp_path)
    assert target.read_text() == "keep"
    assert p.name.endswith("-1.json") and json.loads(p.read_text())["batch_id"] == b["batch_id"]
    assert "Bearer" not in p.read_text()


def test_cron_uses_the_cli_flag_names():
    script = (DM / "scheduled_device_monitoring.sh").read_text()
    for bad in ("--start_date", "--end_date", "--node_ids"):
        assert bad not in script


P = "https://device-monitoring-ingest-prod-685278787484.us-central1.run.app"
T = "https://device-monitoring-ingest-test-685278787484.us-central1.run.app"


def test_ingest_urls_parses_a_comma_list():
    assert publisher.ingest_urls(f" {P}/ , {T},{P} ,") == [P, T]
    assert publisher.ingest_urls("") == []


def test_publish_all_posts_to_every_service(monkeypatch):
    seen = []
    monkeypatch.setattr(publisher.requests, "post",
                        lambda url, **k: seen.append(url) or FakeResponse(201, {"status": "stored"}))
    out = publisher.publish_all(sample(), urls=[P, T], token="t", sleep=lambda s: None)
    assert seen == [f"{P}/v1/batches", f"{T}/v1/batches"] and set(out) == {P, T}


def test_mirror_failure_does_not_fail_the_run(monkeypatch, capsys):
    def post(url, **k):
        return FakeResponse(201, {"status": "stored"}) if url.startswith(P) else FakeResponse(400, {})
    monkeypatch.setattr(publisher.requests, "post", post)
    out = publisher.publish_all(sample(), urls=[P, T], token="t", sleep=lambda s: None)
    assert set(out) == {P} and "mirror" in capsys.readouterr().out


def test_primary_failure_raises_after_trying_the_mirror(monkeypatch):
    seen = []
    def post(url, **k):
        seen.append(url)
        return FakeResponse(400, {}) if url.startswith(P) else FakeResponse(201, {"status": "stored"})
    monkeypatch.setattr(publisher.requests, "post", post)
    with pytest.raises(publisher.PublishError):
        publisher.publish_all(sample(), urls=[P, T], token="t", sleep=lambda s: None)
    assert seen == [f"{P}/v1/batches", f"{T}/v1/batches"]


def test_pinned_secret_refused_with_several_services(monkeypatch):
    monkeypatch.setenv("DEVICEMON_TOKEN_SECRET", "devicemon-ingest-token")
    with pytest.raises(publisher.PublishError):
        publisher.publish_all(sample(), urls=[P, T], token="t")
