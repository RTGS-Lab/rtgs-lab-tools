import base64
import json
import os

import pytest

from rtgs_lab_tools.device_monitoring import ingest_token as it

TEST_URL = "https://device-monitoring-ingest-test-685278787484.us-central1.run.app"
PROD_URL = "https://device-monitoring-ingest-prod-685278787484.us-central1.run.app"
SECRET_VALUE = "s3cr3t-token-value"


def key_file(tmp_path, mode=0o600, body=None):
    p = tmp_path / "sa.json"
    p.write_text(json.dumps(body or {"type": "service_account", "project_id": "rtgslab"}))
    os.chmod(p, mode)
    return p


class Resp:
    def __init__(self, code, body):
        self.status_code, self._body = code, body

    def json(self):
        return self._body


class Session:
    """Stands in for google.auth AuthorizedSession: records the URL, returns a canned reply."""

    def __init__(self, reply):
        self.reply, self.urls = reply, []

    def __call__(self, info):
        assert info["type"] == "service_account"
        return self

    def get(self, url, timeout):
        self.urls.append(url)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def ok_reply(version=3):
    return Resp(200, {"name": f"projects/685278787484/secrets/x/versions/{version}",
                      "payload": {"data": base64.b64encode(SECRET_VALUE.encode()).decode()}})


def test_fetch_latest_version(tmp_path):
    s = Session(ok_reply())
    token, version = it.fetch_from_secret_manager("devicemon-ingest-token-test",
                                                  key_path=key_file(tmp_path), session_factory=s)
    assert token == SECRET_VALUE and version.endswith("/versions/3")
    assert s.urls == ["https://secretmanager.googleapis.com/v1/projects/rtgslab/secrets/"
                      "devicemon-ingest-token-test/versions/latest:access"]


@pytest.mark.parametrize("mode", [0o640, 0o644, 0o660, 0o700])
def test_key_mode_must_be_600(tmp_path, mode):
    with pytest.raises(it.TokenError, match="must be 600"):
        it.fetch_from_secret_manager("devicemon-ingest-token", key_path=key_file(tmp_path, mode),
                                     session_factory=Session(ok_reply()))


def test_missing_key(tmp_path):
    with pytest.raises(it.TokenError, match="not found"):
        it.fetch_from_secret_manager("devicemon-ingest-token", key_path=tmp_path / "nope.json")


def test_symlinked_key_refused(tmp_path):
    link = tmp_path / "link.json"
    link.symlink_to(key_file(tmp_path))
    with pytest.raises(it.TokenError, match="symlink"):
        it.fetch_from_secret_manager("devicemon-ingest-token", key_path=link,
                                     session_factory=Session(ok_reply()))


def test_key_owned_by_someone_else(tmp_path, monkeypatch):
    p = key_file(tmp_path)
    monkeypatch.setattr(it.os, "geteuid", lambda: os.stat(p).st_uid + 1)
    with pytest.raises(it.TokenError, match="not by the running user"):
        it.fetch_from_secret_manager("devicemon-ingest-token", key_path=p,
                                     session_factory=Session(ok_reply()))


def test_not_a_service_account_key(tmp_path):
    with pytest.raises(it.TokenError, match="not a service-account key"):
        it.fetch_from_secret_manager("devicemon-ingest-token",
                                     key_path=key_file(tmp_path, body={"type": "user"}),
                                     session_factory=Session(ok_reply()))


@pytest.mark.parametrize("code,transient", [(403, False), (404, False), (503, True)])
def test_secret_manager_errors_never_echo_a_value(tmp_path, code, transient):
    reply = Resp(code, {"error": {"status": "X", "message": "denied"}})
    with pytest.raises(it.TokenError) as e:
        it.fetch_from_secret_manager("devicemon-ingest-token", key_path=key_file(tmp_path),
                                     session_factory=Session(reply))
    assert f"HTTP {code}" in str(e.value) and e.value.transient is transient
    assert SECRET_VALUE not in str(e.value)


def test_network_error_is_transient(tmp_path):
    with pytest.raises(it.TokenError) as e:
        it.fetch_from_secret_manager("devicemon-ingest-token", key_path=key_file(tmp_path),
                                     session_factory=Session(ConnectionError("down")))
    assert e.value.transient


def test_secret_follows_url_and_pairs():
    assert it.secret_for(TEST_URL, env={}) == "devicemon-ingest-token-test"
    assert it.secret_for(PROD_URL, env={}) == "devicemon-ingest-token"
    with pytest.raises(it.TokenError, match="does not belong"):
        it.secret_for(PROD_URL, env={"DEVICEMON_TOKEN_SECRET": "devicemon-ingest-token-test"})
    with pytest.raises(it.TokenError, match="not a valid secret name"):
        it.secret_for(None, env={"DEVICEMON_TOKEN_SECRET": "../x"})


@pytest.mark.parametrize("url", ["http://device-monitoring-ingest-test-685278787484"
                                 ".us-central1.run.app", "https://attacker.run.app",
                                 "https://device-monitoring-ingest-test-685278787484"
                                 ".us-central1.run.app.evil.com", ""])
def test_unknown_hosts_refused(url):
    with pytest.raises(it.TokenError, match="refusing"):
        it.check_ingest_url(url)


def test_load_token_uses_secret_manager_and_override(capsys):
    seen = []
    tok = it.load_token(TEST_URL, env={}, fetch=lambda s: seen.append(s) or ("abc", "v1"))
    assert tok == "abc" and seen == ["devicemon-ingest-token-test"]
    assert it.load_token(TEST_URL, env={"DEVICEMON_INGEST_TOKEN": "t"},
                         fetch=lambda s: pytest.fail("fetched")) == "t"
    out = capsys.readouterr()
    assert "abc" not in out.out + out.err and "test override" in out.err


def test_publish_end_to_end_with_mocked_secret_manager(tmp_path, monkeypatch):
    from rtgs_lab_tools.device_monitoring import publisher
    from tests.device_monitoring.test_publisher import FakeResponse, sample

    monkeypatch.delenv("DEVICEMON_INGEST_TOKEN", raising=False)
    monkeypatch.delenv("DEVICEMON_TOKEN_SECRET", raising=False)
    monkeypatch.setenv("DEVICEMON_SA_KEY", str(key_file(tmp_path)))
    monkeypatch.setattr(it, "_session", Session(ok_reply()))
    monkeypatch.setattr(it.fetch_from_secret_manager, "__defaults__",
                        (None, None, Session(ok_reply())))
    sent = {}
    monkeypatch.setattr(publisher.requests, "post", lambda url, data, headers, timeout:
                        sent.update(url=url, auth=headers["Authorization"])
                        or FakeResponse(201, {"status": "stored"}))
    publisher.publish(sample(), url=TEST_URL + "/")
    assert sent == {"url": TEST_URL + "/v1/batches", "auth": f"Bearer {SECRET_VALUE}"}
