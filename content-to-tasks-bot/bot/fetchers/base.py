from abc import ABC, abstractmethod

from bot.models import FetchedContent


class BaseFetcher(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool: ...

    @abstractmethod
    def fetch(self, url: str) -> FetchedContent: ...
