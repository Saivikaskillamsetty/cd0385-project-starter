"""Basic tests for the analyzer module (no API calls)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from bot.analyzer import analyze_content
from bot.models import ExtractedTask, FetchedContent


SAMPLE_RESPONSE = {
    "tasks": [
        {
            "title": "Integrate QuantLib for bond pricing",
            "description": "Use QuantLib's Python bindings to price fixed-income instruments. The library provides built-in yield curve models and day count conventions.",
            "priority": "High",
            "categories": ["Finance", "API Integration"],
            "effort": "Half-day",
        }
    ]
}


def _make_content() -> FetchedContent:
    return FetchedContent(
        url="https://example.com/finance-article",
        source_type="article",
        title="Top Python Finance Libraries",
        body="QuantLib is a powerful open-source library for quantitative finance...",
        fetch_method="scraped",
    )


@patch("bot.analyzer.anthropic.Anthropic")
def test_analyze_content_returns_tasks(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(SAMPLE_RESPONSE))]
    mock_client.messages.create.return_value = mock_message

    tasks = analyze_content(_make_content())

    assert len(tasks) == 1
    task = tasks[0]
    assert isinstance(task, ExtractedTask)
    assert task.title == "Integrate QuantLib for bond pricing"
    assert task.priority == "High"
    assert "Finance" in task.categories
    assert task.source_url == "https://example.com/finance-article"
    assert task.source_type == "article"


@patch("bot.analyzer.anthropic.Anthropic")
def test_analyze_content_retries_on_bad_json(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    good_response = MagicMock()
    good_response.content = [MagicMock(text=json.dumps(SAMPLE_RESPONSE))]

    bad_response = MagicMock()
    bad_response.content = [MagicMock(text="```json\nnot valid```")]

    mock_client.messages.create.side_effect = [bad_response, good_response]

    tasks = analyze_content(_make_content())
    assert len(tasks) == 1
    assert mock_client.messages.create.call_count == 2
