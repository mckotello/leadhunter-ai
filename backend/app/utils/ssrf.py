import ipaddress
import socket
from urllib.parse import urlparse

from app.config import settings


class SSRFError(ValueError):
    pass


def validate_public_url(url: str) -> str:
    parsed = urlparse(url.strip())
    schemes = {s.strip().lower() for s in settings.allowed_url_schemes.split(",")}
    if parsed.scheme not in schemes:
        raise SSRFError(f"Недопустимая схема URL: {parsed.scheme}")
    if not parsed.hostname:
        raise SSRFError("URL без хоста")

    host = parsed.hostname.lower()
    if settings.block_private_networks:
        if host in {"localhost", "127.0.0.1", "::1"}:
            raise SSRFError("Локальные адреса запрещены")
        try:
            addr = ipaddress.ip_address(host)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                raise SSRFError("Приватные адреса запрещены")
        except ValueError:
            try:
                infos = socket.getaddrinfo(host, parsed.port or 443)
            except socket.gaierror as exc:
                raise SSRFError(f"Не удалось разрешить хост: {host}") from exc
            for info in infos:
                ip = ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    raise SSRFError("Приватные адреса запрещены")

    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path or ''}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized.rstrip("/") or normalized
