from unittest.mock import patch

import httpx
import pytest

from app.utils.ssrf import SSRFError, assert_host_resolves_to_public_ips, safe_fetch_html, validate_public_url


def test_ssrf_blocks_literal_private_ip():
    with pytest.raises(SSRFError):
        validate_public_url("http://192.168.1.1/")


def test_ssrf_blocks_metadata_ip():
    with pytest.raises(SSRFError):
        validate_public_url("http://169.254.169.254/latest/meta-data/")


def test_ssrf_blocks_localhost_name():
    with pytest.raises(SSRFError):
        validate_public_url("http://localhost/admin")


def test_ssrf_dns_rebinding_private_resolution():
    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host == "evil.example":
            return [(2, 1, 6, "", ("127.0.0.1", port))]
        raise OSError("unexpected host")

    with patch("app.utils.ssrf.socket.getaddrinfo", side_effect=fake_getaddrinfo):
        with pytest.raises(SSRFError, match="запрещённый адрес"):
            assert_host_resolves_to_public_ips("evil.example", 443)


@pytest.mark.asyncio
async def test_safe_fetch_blocks_redirect_to_localhost():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})
        return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, follow_redirects=False) as client:
        with patch("app.utils.ssrf.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
            with pytest.raises(SSRFError):
                await safe_fetch_html(client, "https://public.test/start", {})


@pytest.mark.asyncio
async def test_safe_fetch_follows_public_redirect():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/start":
            return httpx.Response(302, headers={"Location": "/final"})
        return httpx.Response(200, text="<html>ok</html>", headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        follow_redirects=False,
        base_url="https://public.test",
    ) as client:
        with patch("app.utils.ssrf.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
            html, final = await safe_fetch_html(client, "https://public.test/start", {})
    assert html == "<html>ok</html>"
    assert final.endswith("/final")
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_safe_fetch_revalidates_dns_on_each_hop():
    with patch("app.utils.ssrf.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]) as mocked:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/a":
                return httpx.Response(302, headers={"Location": "https://public.test/b"})
            return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, follow_redirects=False) as client:
            await safe_fetch_html(client, "https://public.test/a", {}, max_redirects=3)
    assert mocked.call_count >= 2
