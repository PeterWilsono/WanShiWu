"""网页抓取安全限制测试；不访问真实网络。"""

import socket

import pytest

from app.modules.inbox import fetcher as fetcher_module
from app.modules.inbox.fetcher import FetchError, fetch_article, validate_public_url


def public_dns(host, port, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/a",
        "http://127.0.0.1/a",
        "http://10.0.0.2/a",
        "http://192.168.1.2/a",
        "http://169.254.1.2/a",
        "http://[::1]/a",
    ],
)
def test_rejects_local_private_and_link_local_urls(url: str) -> None:
    with pytest.raises(FetchError):
        validate_public_url(url)


def test_accepts_hostname_only_when_all_dns_results_are_public(monkeypatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    assert validate_public_url("HTTPS://Example.COM/a#b") == "https://example.com/a"


def test_rejects_hostname_when_any_dns_result_is_private(monkeypatch) -> None:
    def mixed_dns(host, port, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.3", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", mixed_dns)
    with pytest.raises(FetchError, match="内网"):
        validate_public_url("https://example.com")


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b"<html></html>"):
        self.status_code = status
        self.headers = headers or {}
        self.body = body
        self.encoding = "utf-8"
        self.is_redirect = status in {301, 302, 303, 307, 308}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def raise_for_status(self):
        return None

    def iter_bytes(self):
        yield self.body


class FakeClient:
    responses = []
    calls = []

    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def stream(self, method, url):
        self.calls.append(url)
        return self.responses.pop(0)


def test_redirect_targets_are_validated_again(monkeypatch) -> None:
    FakeClient.responses = [FakeResponse(302, {"Location": "http://127.0.0.1/private"})]
    FakeClient.calls = []
    monkeypatch.setattr(fetcher_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    with pytest.raises(FetchError, match="内网|本机"):
        fetch_article("https://example.com/start")
    assert FakeClient.calls == ["https://example.com/start"]


def test_reads_html_within_size_limit_and_extracts_content(monkeypatch) -> None:
    FakeClient.responses = [
        FakeResponse(
            200,
            {"Content-Type": "text/html; charset=utf-8", "Content-Length": "80"},
            b"<html><head><title>A title</title></head><body>article</body></html>",
        )
    ]
    monkeypatch.setattr(fetcher_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    monkeypatch.setattr(fetcher_module.trafilatura, "extract", lambda *args, **kwargs: "正文")
    article = fetch_article("https://example.com/article")
    assert article.title == "A title"
    assert article.content == "正文"


def test_rejects_non_html_and_oversized_responses(monkeypatch) -> None:
    monkeypatch.setattr(fetcher_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    FakeClient.responses = [FakeResponse(200, {"Content-Type": "application/pdf"})]
    with pytest.raises(FetchError, match="HTML"):
        fetch_article("https://example.com/file")

    FakeClient.responses = [
        FakeResponse(200, {"Content-Type": "text/html", "Content-Length": str(2 * 1024 * 1024 + 1)})
    ]
    with pytest.raises(FetchError, match="2MB"):
        fetch_article("https://example.com/large")
