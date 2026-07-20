import json
from pathlib import Path

import pytest

from literehab.mobile_access import (
    MobileAccessConfig,
    authorization_matches,
    create_pairing_payload,
    load_or_create_token,
    render_pairing_qr,
)


def test_token_is_persistent_and_private(tmp_path: Path):
    path = tmp_path / "mobile-token"

    first = load_or_create_token(path)
    second = load_or_create_token(path)

    assert first == second
    assert len(first) >= 32
    assert path.stat().st_mode & 0o777 == 0o600


def test_empty_token_file_is_replaced(tmp_path: Path):
    path = tmp_path / "mobile-token"
    path.write_text("\n", encoding="utf-8")

    token = load_or_create_token(path)

    assert len(token) >= 32
    assert path.read_text(encoding="utf-8").strip() == token


def test_pairing_payload_is_versioned():
    config = MobileAccessConfig(token="secret-token", api_version=1)

    assert create_pairing_payload(config, "192.168.1.8", 8000) == {
        "version": 1,
        "name": "LiteRehab Mac",
        "base_url": "http://192.168.1.8:8000",
        "pairing_token": "secret-token",
    }


@pytest.mark.parametrize(
    "header",
    [None, "", "Basic secret-token", "Bearer wrong", "Bearer secret-token-extra"],
)
def test_authorization_rejects_invalid_headers(header):
    assert not authorization_matches(MobileAccessConfig("secret-token"), header)


def test_authorization_accepts_matching_bearer_token():
    assert authorization_matches(
        MobileAccessConfig("secret-token"),
        "Bearer secret-token",
    )


def test_qr_renderer_encodes_compact_json(monkeypatch):
    encoded = []
    printed = []

    class FakeQr:
        def add_data(self, value):
            encoded.append(value)

        def make(self, fit):
            assert fit is True

        def print_ascii(self, invert):
            printed.append(invert)

    monkeypatch.setattr("literehab.mobile_access.qrcode.QRCode", lambda **_: FakeQr())
    payload = create_pairing_payload(
        MobileAccessConfig("secret-token"),
        "192.168.1.8",
        8000,
    )

    render_pairing_qr(payload)

    assert json.loads(encoded[0]) == payload
    assert ": " not in encoded[0]
    assert ", " not in encoded[0]
    assert printed == [True]
