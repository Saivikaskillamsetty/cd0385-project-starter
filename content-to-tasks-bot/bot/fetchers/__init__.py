from bot.fetchers.base import BaseFetcher
from bot.fetchers.generic import GenericFetcher
from bot.fetchers.instagram import InstagramFetcher
from bot.fetchers.twitter import TwitterFetcher
from bot.fetchers.youtube import YouTubeFetcher


def get_fetcher(url: str) -> BaseFetcher:
    for fetcher in [TwitterFetcher(), InstagramFetcher(), YouTubeFetcher()]:
        if fetcher.can_handle(url):
            return fetcher
    return GenericFetcher()
