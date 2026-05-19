from dataclasses import dataclass, field


@dataclass
class FetchedContent:
    url: str
    source_type: str  # "twitter" | "instagram" | "youtube" | "article"
    title: str
    body: str
    fetch_method: str  # "scraped" | "oembed" | "manual_fallback"
    author: str | None = None


@dataclass
class ExtractedTask:
    title: str
    description: str
    priority: str  # "High" | "Medium" | "Low"
    categories: list[str]
    effort: str  # "Quick (<1hr)" | "1-2hrs" | "Half-day" | "Multi-day"
    source_url: str
    source_type: str
    raw_claude_json: dict = field(default_factory=dict)
