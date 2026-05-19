import requests
from bs4 import BeautifulSoup

from bot.fetchers.base import BaseFetcher
from bot.models import FetchedContent

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
MAX_BODY_CHARS = 12_000


class GenericFetcher(BaseFetcher):
    def can_handle(self, url: str) -> bool:
        return True  # catch-all

    def fetch(self, url: str) -> FetchedContent:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except requests.RequestException:
            return FetchedContent(
                url=url,
                source_type="article",
                title=url,
                body="",
                fetch_method="manual_fallback",
            )

        soup = BeautifulSoup(resp.text, "lxml")

        title = _extract_title(soup)
        body = _extract_body(soup)
        author = _extract_author(soup)

        return FetchedContent(
            url=url,
            source_type="article",
            title=title,
            body=body[:MAX_BODY_CHARS],
            fetch_method="scraped",
            author=author,
        )


def _extract_title(soup: BeautifulSoup) -> str:
    for selector in [
        lambda s: s.find("meta", property="og:title"),
        lambda s: s.find("h1"),
        lambda s: s.find("title"),
    ]:
        tag = selector(soup)
        if tag:
            return tag.get("content") or tag.get_text(strip=True)
    return ""


def _extract_body(soup: BeautifulSoup) -> str:
    for tag_name in ("article", "main"):
        tag = soup.find(tag_name)
        if tag:
            return " ".join(tag.get_text(" ", strip=True).split())

    paragraphs = soup.find_all("p")
    return " ".join(p.get_text(" ", strip=True) for p in paragraphs)


def _extract_author(soup: BeautifulSoup) -> str | None:
    meta = soup.find("meta", attrs={"name": "author"})
    if meta:
        return meta.get("content")
    link = soup.find("a", rel=lambda r: r and "author" in r)
    if link:
        return link.get_text(strip=True)
    return None
