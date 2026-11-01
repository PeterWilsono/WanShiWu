"""受限网页抓取：SSRF 校验、重定向复查、超时与响应大小限制。"""

import html
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx
import trafilatura

from app.modules.inbox.schemas import normalize_url

MAX_CONTENT_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
USER_AGENT = "WanShiWuPersonalReader/1.0 (+personal bookmark archiving)"


class FetchError(Exception):
    """可安全展示给用户的抓取失败原因。"""


@dataclass(frozen=True)
class FetchedArticle:
    title: str | None
    content: str


def validate_public_url(url: str) -> str:
    normalized = normalize_url(url)
    parsed = urlsplit(normalized)
    host = parsed.hostname or ""
    if host.lower() == "localhost" or host.lower().endswith(".localhost"):
        raise FetchError("不允许抓取本机地址")
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None
    if literal_ip is not None and not literal_ip.is_global:
        raise FetchError("不允许抓取内网、本机或保留地址")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchError("无法解析网页域名") from exc
    if not addresses:
        raise FetchError("无法解析网页域名")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise FetchError("不允许抓取内网、本机或保留地址")
    return normalized


def _html_title(document: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", document, flags=re.I | re.S)
    if not match:
        return None
    title = html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()
    return title[:300] or None


def fetch_article(url: str) -> FetchedArticle:
    current = normalize_url(url)
    timeout = httpx.Timeout(10.0, connect=10.0, read=10.0, write=10.0, pool=10.0)
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        ) as client:
            for redirect_count in range(MAX_REDIRECTS + 1):
                current = validate_public_url(current)
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        if redirect_count >= MAX_REDIRECTS:
                            raise FetchError("网页重定向次数过多")
                        location = response.headers.get("Location")
                        if not location:
                            raise FetchError("网页重定向缺少目标地址")
                        current = urljoin(current, location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
                    if content_type.lower() != "text/html":
                        raise FetchError("只支持抓取 HTML 网页")
                    length = response.headers.get("Content-Length")
                    if length and int(length) > MAX_CONTENT_BYTES:
                        raise FetchError("网页内容超过 2MB 限制")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_CONTENT_BYTES:
                            raise FetchError("网页内容超过 2MB 限制")
                        chunks.append(chunk)
                    document = b"".join(chunks).decode(
                        response.encoding or "utf-8", errors="replace"
                    )
                    content = trafilatura.extract(
                        document, include_comments=False, include_tables=False
                    )
                    if not content or not content.strip():
                        raise FetchError("未能从网页提取正文，请手动粘贴")
                    return FetchedArticle(title=_html_title(document), content=content.strip())
    except FetchError:
        raise
    except httpx.TimeoutException as exc:
        raise FetchError("网页抓取超时") from exc
    except httpx.HTTPStatusError as exc:
        raise FetchError(f"网页返回 HTTP {exc.response.status_code}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise FetchError("网页抓取失败，请稍后重试或手动粘贴正文") from exc
    raise FetchError("网页抓取失败")
