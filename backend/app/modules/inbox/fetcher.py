"""受限网页抓取：SSRF 校验、重定向复查、编码识别与双层正文提取。"""

import html
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx
import trafilatura
from lxml import etree
from lxml import html as lxml_html

from app.modules.inbox.schemas import normalize_url

MAX_CONTENT_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 "
    "WanShiWuPersonalReader/1.1"
)
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
MANUAL_CONTENT_HINT = "请打开原文并手动粘贴正文"


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


def _decode_document(body: bytes, encoding: str | None) -> str:
    declared = encoding
    if not declared:
        head = body[:4096].decode("ascii", errors="ignore")
        match = re.search(r"charset=[\"']?([a-zA-Z0-9_-]+)", head, flags=re.I)
        declared = match.group(1) if match else None
    for candidate in (declared, "utf-8", "gb18030"):
        if not candidate:
            continue
        try:
            return body.decode(candidate)
        except (UnicodeDecodeError, LookupError):
            continue
    return body.decode("utf-8", errors="replace")


def _fallback_text(document: str) -> str | None:
    """正文识别器失败时，从 article/main/body 提取可读文本并剔除明显噪声。"""
    try:
        root = lxml_html.fromstring(document)
    except (etree.LxmlError, ValueError, TypeError):
        return None
    noisy = "//script|//style|//noscript|//svg|//nav|//footer|//form|//aside"
    for element in root.xpath(noisy):
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    candidates = root.xpath("//article|//main")
    target = max(candidates, key=lambda item: len(item.text_content()), default=None)
    if target is None:
        body = root.find("body")
        target = body if body is not None else root
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in target.text_content().splitlines()
        if line.strip()
    ]
    content = "\n".join(line for line in lines if line).strip()
    return content if len(content) >= 40 else None


def _extract_content(document: str) -> str | None:
    extracted = trafilatura.extract(
        document,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    if extracted and extracted.strip():
        return extracted.strip()
    return _fallback_text(document)


def fetch_article(url: str) -> FetchedArticle:
    current = normalize_url(url)
    timeout = httpx.Timeout(10.0, connect=10.0, read=10.0, write=10.0, pool=10.0)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers=headers,
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
                    content_type = content_type.strip().lower()
                    if content_type and content_type not in HTML_CONTENT_TYPES:
                        raise FetchError("只支持抓取 HTML 网页，PDF 或文件请下载后粘贴正文")
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
                    body = b"".join(chunks)
                    if not content_type and not re.match(
                        rb"\s*(?:<!doctype\s+html|<html|<\?xml)", body, flags=re.I
                    ):
                        raise FetchError("网页没有返回可识别的 HTML 内容")
                    document = _decode_document(body, response.encoding)
                    content = _extract_content(document)
                    if not content:
                        raise FetchError(
                            f"自动提取不到正文，网页可能需要登录、验证或动态渲染；{MANUAL_CONTENT_HINT}"
                        )
                    return FetchedArticle(title=_html_title(document), content=content)
    except FetchError:
        raise
    except httpx.TimeoutException as exc:
        raise FetchError(f"网页抓取超时，{MANUAL_CONTENT_HINT}") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in {401, 403}:
            raise FetchError(
                f"网站拒绝自动访问，可能需要登录或验证；{MANUAL_CONTENT_HINT}"
            ) from exc
        if status == 404:
            raise FetchError("网页不存在或已被删除，请检查链接") from exc
        raise FetchError(f"网页返回 HTTP {status}，{MANUAL_CONTENT_HINT}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise FetchError(f"网页抓取失败，请稍后重试或{MANUAL_CONTENT_HINT}") from exc
    raise FetchError("网页抓取失败")
