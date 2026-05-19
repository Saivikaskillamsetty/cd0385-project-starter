import re

import requests
from bs4 import BeautifulSoup

from bot.fetchers.base import BaseFetcher
from bot.models import FetchedContent

TWITTER_PATTERN = re.compile(r"(twitter\.com|x\.com)/\w+/status/")
OEMBED_URL = "https://publish.twitter.com/oembed"


class TwitterFetcher(BaseFetcher):
    def can_handle(self, url: str) -> bool:
        return bool(TWITTER_PATTERN.search(url))

    def fetch(self, url: str) -> FetchedContent:
        try:
            resp = requests.get(
                OEMBED_URL, params={"url": url}, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            html = data.get("html", "")
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text(" ", strip=True)
            author = data.get("author_name")

            if text:
                return FetchedContent(
                    url=url,
                    source_type="twitter",
                    title=f"Tweet by {author}" if author else "Tweet",
                    body=text,
                    fetch_method="oembed",
                    author=author,
                )
        except requests.RequestException:
            pass

        return FetchedContent(
            url=url,
            source_type="twitter",
            title="Tweet",
            body="",
            fetch_method="manual_fallback",
        )
