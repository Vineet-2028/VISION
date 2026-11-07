"""Local Wi-Fi gateway: pinned ephemeral TLS and a loopback-only QR operator page."""

import argparse
import base64
import hashlib
import html
import io
import ipaddress
import json
import secrets
import ssl
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import qrcode
import qrcode.image.svg
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from perception_lab.field_gateway import FieldHTTPServer, Gateway
from perception_lab.field_pairing import PairingAuthority


def certificate(directory, address):
    ip = ipaddress.ip_address(address)
    if ip.version != 4 or not ip.is_private or ip.is_unspecified or ip.is_multicast:
        raise ValueError("Use the PC's private IPv4 address")
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "VISION local gateway")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    key_path, cert_path = directory / "key.pem", directory / "cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert_path, key_path)
    der = cert.public_bytes(serialization.Encoding.DER)
    return context, hashlib.sha256(der).hexdigest(), base64.b64encode(der).decode()


def portal(authority, endpoint, fingerprint, certificate_der, gateway, port):
    nonce = secrets.token_urlsafe(32)

    class Operator(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def allowed(self):
            return self.headers.get("Host") == f"127.0.0.1:{port}"

        def do_GET(self):
            if not self.allowed() or self.path != "/":
                self.send_error(404)
                return
            payload = json.dumps(
                {
                    "schema": "VISION_PAIR_V1",
                    "endpoint": endpoint,
                    "fingerprint": fingerprint,
                    "certificate": certificate_der,
                    "code": authority.issue(),
                },
                separators=(",", ":"),
            )
            image = qrcode.make(payload, image_factory=qrcode.image.svg.SvgPathImage)
            buffer = io.BytesIO()
            image.save(buffer)
            svg = buffer.getvalue().decode()
            page = f'''<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>Pair VISION</title>
<body style="font:18px system-ui;max-width:720px;margin:40px auto;padding:20px">
<h1>Pair your phone</h1>
<p>PC and phone must be on the same trusted Wi-Fi.
Scan only this operator screen. Code expires in two minutes and can be used once.</p>
<div style="max-width:420px">{svg}</div>
<p>Keep this PC running. Refresh this page to replace the code.</p>
<details>
<summary>Manual pairing payload</summary>
<textarea readonly rows="7" style="width:100%">{html.escape(payload)}</textarea>
</details>
<details>
<summary>Desktop Lab connection</summary>
<p>Loopback gateway: http://127.0.0.1:8765</p>
<p>Operator token (keep private): <code>{gateway.token}</code>
</p>
</details>
<form method="post">
<input type="hidden" name="nonce" value="{nonce}">
<button>Revoke all paired access and stop session</button>
</form>
<p>No public exposure. No camera files are recorded by default.</p>
</body>
</html>'''.encode()
            self.send_response(200)
            for key, value in {
                "Content-Type": "text/html; charset=utf-8",
                "Content-Length": str(len(page)),
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'none'; style-src 'unsafe-inline'; "
                    "form-action 'self'; frame-ancestors 'none'"
                ),
                "Referrer-Policy": "no-referrer",
            }.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            from urllib.parse import parse_qs

            if (
                not self.allowed()
                or self.headers.get("Origin") != f"http://127.0.0.1:{port}"
                or self.headers.get("Transfer-Encoding")
            ):
                self.send_error(403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length < 256:
                    raise ValueError()
                data = parse_qs(self.rfile.read(length).decode())
                if not secrets.compare_digest(data.get("nonce", [""])[0], nonce):
                    raise ValueError()
            except (ValueError, UnicodeError):
                self.send_error(403)
                return
            with gateway.lock:
                authority.revoke()
                if gateway.session:
                    gateway.session.close()
                gateway.pending.take()
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        def setup(self):
            self.request.settimeout(2)
            super().setup()

    return HTTPServer(("127.0.0.1", port), Operator)


def main():
    from alpha_field_gateway import WorkerHost, hash_file, release_profile

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", required=True, help="PC private Wi-Fi IPv4, e.g. 192.168.1.20")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = root / "benchmark-results/v02/VISION_CONTROLLED_ALPHA_V1/manifest.json"
    manifest_hash = hash_file(manifest)
    if manifest_hash != "ecd83215cc8f8e144ec9126b61415e8ca38b854a4126cfdbc6e52d55affa6254":
        raise ValueError("Wireless Alpha requires the qualified release manifest")
    authority = PairingAuthority()
    gateway = Gateway(secrets.token_urlsafe(32), manifest_hash)
    runtime = [
        root / "benchmark-results/v0-rescue" / p
        for p in ("gpu-runtime", "gpu-libraries", "cudnn-9.10/nvidia/cudnn/bin")
    ]
    host = WorkerHost(gateway, release_profile(manifest), runtime)
    with tempfile.TemporaryDirectory(prefix="vision-tls-") as temporary:
        tls, fingerprint, certificate_der = certificate(Path(temporary), args.address)
        with (
            FieldHTTPServer((args.address, args.port), gateway, tls, authority) as wireless,
            FieldHTTPServer(("127.0.0.1", 8765), gateway) as local,
            portal(
                authority,
                f"https://{args.address}:{args.port}",
                fingerprint,
                certificate_der,
                gateway,
                8766,
            ) as page,
        ):
            for server in (wireless, local):
                threading.Thread(target=server.serve_forever, daemon=True).start()
            host.start()
            print(
                "Open http://127.0.0.1:8766 on this PC to pair. Ctrl+C revokes all access.",
                flush=True,
            )
            try:
                page.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                authority.revoke()
                wireless.shutdown()
                local.shutdown()
                host.close()


if __name__ == "__main__":
    main()
