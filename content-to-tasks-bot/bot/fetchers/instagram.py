import os
import re

import requests

from bot.fetchers.base import BaseFetcher
from bot.models import FetchedContent

INSTAGRAM_PATTERN = re.compile(r"instagram\.com/(p|reel|tv)/")
OEMBED_URL = "https://graph.facebook.com/v18.0/instagram_oembed"


class InstagramFetcher(BaseFetcher):
    def can_handle(self, url: str) -> bool:
        return bool(INSTAGRAM_PATTERN.search(url))

    def fetch(self, url: str) -> FetchedContent:
        token = os.environ.get("INSTAGRAM_BASIC_DISPLAY_TOKEN")
        if token:
            try:
                resp = requests.get(
                    OEMBED_URL,
                    params={"url": url, "access_token": token},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                title = data.get("title") or data.get("author_name", "Instagram post")
                author = data.get("author_name")
                if title:
                    return FetchedContent(
                        url=url,
                        source_type="instagram",
                        title=title,
                        body=title,
                        fetch_method="oembed",
                        author=author,
                    )
            except requests.RequestException:
                pass

        return FetchedContent(
            url=url,
            source_type="instagram",
            title="Instagram post",
            body="",
            fetch_method="manual_fallback",
        )
