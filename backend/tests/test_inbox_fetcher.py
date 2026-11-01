"""网页抓取安全限制测试；不访问真实网络。"""

import socket

import httpx
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
    def __init__(self, status=200, headers=None, body=b"<html></html>", encoding="utf-8"):
        self.status_code = status
        self.headers = headers or {}
        self.body = body
        self.encoding = encoding
        self.is_redirect = status in {301, 302, 303, 307, 308}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.com/article")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("HTTP error", request=request, response=response)

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


def test_fallback_extracts_article_text_when_primary_extractor_fails(monkeypatch) -> None:
    document = """
    <html><head><title>静态文章</title></head><body>
      <nav>导航首页和登录链接</nav>
      <article><h1>清淡饮食</h1><p>这是一段足够长的正文内容，用来验证正文兜底提取能够保留真正文章。</p>
      <p>第二个段落也应该被完整保存，方便后续生成摘要。</p></article>
      <script>不应进入正文</script>
    </body></html>
    """
    FakeClient.responses = [
        FakeResponse(200, {"Content-Type": "application/xhtml+xml"}, document.encode())
    ]
    monkeypatch.setattr(fetcher_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    monkeypatch.setattr(fetcher_module.trafilatura, "extract", lambda *args, **kwargs: None)

    article = fetch_article("https://example.com/xhtml")

    assert "清淡饮食" in article.content
    assert "第二个段落" in article.content
    assert "导航首页" not in article.content
    assert "不应进入正文" not in article.content


def test_sniffs_missing_html_content_type_and_meta_charset(monkeypatch) -> None:
    document = (
        '<html><head><meta charset="gb18030"><title>中文网页</title></head>'
        "<body>正文</body></html>"
    )
    FakeClient.responses = [
        FakeResponse(200, {}, document.encode("gb18030"), encoding=None)
    ]
    monkeypatch.setattr(fetcher_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    monkeypatch.setattr(fetcher_module.trafilatura, "extract", lambda *args, **kwargs: "中文正文")

    article = fetch_article("https://example.com/chinese")

    assert article.title == "中文网页"
    assert article.content == "中文正文"


def test_access_denied_explains_manual_content_fallback(monkeypatch) -> None:
    FakeClient.responses = [FakeResponse(403, {"Content-Type": "text/html"})]
    monkeypatch.setattr(fetcher_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)

    with pytest.raises(FetchError, match="登录|验证") as caught:
        fetch_article("https://example.com/private")

    assert "手动粘贴正文" in str(caught.value)
