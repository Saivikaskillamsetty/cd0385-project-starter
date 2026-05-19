import re

import requests
from bs4 import BeautifulSoup

from bot.fetchers.base import BaseFetcher
from bot.models import FetchedContent

OEMBED_URL = "https://www.youtube.com/oembed"
YOUTUBE_PATTERN = re.compile(
    r"(youtube\.com/watch|youtu\.be/|youtube\.com/shorts/)"
)


class YouTubeFetcher(BaseFetcher):
    def can_handle(self, url: str) -> bool:
        return bool(YOUTUBE_PATTERN.search(url))

    def fetch(self, url: str) -> FetchedContent:
        try:
            resp = requests.get(
                OEMBED_URL, params={"url": url, "format": "json"}, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            title = data.get("title", "")
            author = data.get("author_name")
        except requests.RequestException:
            title = ""
            author = None

        description = _scrape_description(url)

        body = description or title
        if not body:
            return FetchedContent(
                url=url,
                source_type="youtube",
                title=title or url,
                body="",
                fetch_method="manual_fallback",
                author=author,
            )

        return FetchedContent(
            url=url,
            source_type="youtube",
            title=title,
            body=body,
            fetch_method="oembed",
            author=author,
        )


def _scrape_description(url: str) -> str:
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            return meta.get("content", "")
        og = soup.find("meta", property="og:description")
        if og:
            return og.get("content", "")
    except requests.RequestException:
        pass
    return ""
