import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

from app.config import settings

REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})

BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "metadata.google.internal",
        "metadata.goog",
    }
)

CLOUD_METADATA_IPV4 = ipaddress.ip_address("169.254.169.254")


class SSRFError(ValueError):
    pass


def is_blocked_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if addr == CLOUD_METADATA_IPV4:
        return True
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def assert_host_resolves_to_public_ips(host: str, port: int | None) -> None:
    """Проверка DNS: все A/AAAA записи должны указывать на публичные адреса (anti DNS rebinding)."""
    host = host.lower().rstrip(".")
    if host in BLOCKED_HOSTNAMES:
        raise SSRFError(f"Запрещённый хост: {host}")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if is_blocked_ip(literal):
            raise SSRFError("Приватные и служебные адреса запрещены")
        return

    connect_port = port or 443
    try:
        infos = socket.getaddrinfo(host, connect_port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFError(f"Не удалось разрешить хост: {host}") from exc

    if not infos:
        raise SSRFError(f"Пустой DNS-ответ для хоста: {host}")

    for info in infos:
        resolved = ipaddress.ip_address(info[4][0])
        if is_blocked_ip(resolved):
            raise SSRFError(
                f"Хост {host} резолвится в запрещённый адрес {resolved}"
            )


def _reject_blocked_host(host: str, port: int | None) -> None:
    """Литералы IP и DNS — единая точка проверки перед каждым HTTP-hop."""
    if not settings.block_private_networks:
        return
    assert_host_resolves_to_public_ips(host, port)


def validate_public_url(url: str, *, resolve_dns: bool = True) -> str:
    parsed = urlparse(url.strip())
    schemes = {s.strip().lower() for s in settings.allowed_url_schemes.split(",")}
    if parsed.scheme not in schemes:
        raise SSRFError(f"Недопустимая схема URL: {parsed.scheme}")
    if not parsed.hostname:
        raise SSRFError("URL без хоста")

    if resolve_dns:
        _reject_blocked_host(parsed.hostname, parsed.port)

    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path or ''}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized.rstrip("/") or normalized


async def safe_fetch_html(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    *,
    max_redirects: int | None = None,
) -> tuple[str | None, str]:
    """
    GET с ручной обработкой redirect: каждый hop валидируется и повторно резолвится в DNS.
    """
    limit = max_redirects if max_redirects is not None else settings.http_max_redirects
    current = validate_public_url(url)

    for hop in range(limit + 1):
        parsed = urlparse(current)
        _reject_blocked_host(parsed.hostname or "", parsed.port)

        response = await client.get(current, headers=headers, follow_redirects=False)

        if response.status_code in REDIRECT_STATUS_CODES:
            location = response.headers.get("location")
            if not location:
                raise SSRFError("Redirect без заголовка Location")
            next_url = urljoin(current, location.strip())
            current = validate_public_url(next_url)
            continue

        if response.status_code >= 400:
            return None, current

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return None, current

        return response.text, str(response.url)

    raise SSRFError(f"Превышено число перенаправлений ({limit})")
