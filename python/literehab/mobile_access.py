from __future__ import annotations

import json
import secrets
import socket
from dataclasses import dataclass
from pathlib import Path

import qrcode


@dataclass(frozen=True)
class MobileAccessConfig:
    token: str
    api_version: int = 1
    service_name: str = "LiteRehab Mac"


def load_or_create_token(path: Path) -> str:
    if path.is_file():
        token = path.read_text(encoding="utf-8").strip()
        if token:
            path.chmod(0o600)
            return token

    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    path.write_text(f"{token}\n", encoding="utf-8")
    path.chmod(0o600)
    return token


def create_pairing_payload(
    config: MobileAccessConfig,
    host: str,
    port: int,
) -> dict[str, object]:
    return {
        "version": config.api_version,
        "name": config.service_name,
        "base_url": f"http://{host}:{port}",
        "pairing_token": config.token,
    }


def authorization_matches(
    config: MobileAccessConfig,
    header: str | None,
) -> bool:
    prefix = "Bearer "
    if header is None or not header.startswith(prefix):
        return False
    return secrets.compare_digest(config.token, header[len(prefix):])


def detect_lan_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("192.0.2.1", 80))
        return str(probe.getsockname()[0])


def render_pairing_qr(payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, separators=(",", ":"))
    qr = qrcode.QRCode(border=2)
    qr.add_data(encoded)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
