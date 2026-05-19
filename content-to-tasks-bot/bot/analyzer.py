import json

import anthropic

from bot.models import ExtractedTask, FetchedContent

SYSTEM_PROMPT = """\
You are a personal productivity assistant that reads content from social media, \
articles, and videos, then extracts a list of concrete, actionable tasks the reader \
should add to their project TODO list.

Focus on things a software developer would actually want to explore, build, integrate, \
or learn. Be specific — instead of "learn about X", say "Implement X feature using \
Y library by following Z approach mentioned in the article."

Return ONLY valid JSON — no markdown fences, no commentary outside the JSON.\
"""

USER_PROMPT_TEMPLATE = """\
Analyze the following content from {source_type} ({url}).

CONTENT:
---
{title}

{body}
---

Extract between 1 and 8 actionable tasks from this content.

Return a JSON object in exactly this structure:
{{
  "tasks": [
    {{
      "title": "Short imperative action (max 80 chars)",
      "description": "2-4 sentences describing what to do and why it is useful. Be specific.",
      "priority": "High | Medium | Low",
      "categories": ["Category1", "Category2"],
      "effort": "Quick (<1hr) | 1-2hrs | Half-day | Multi-day"
    }}
  ]
}}

Priority guidelines:
- High: directly applicable to current projects, foundational concepts
- Medium: interesting exploration, future projects
- Low: nice-to-know, reference material

Category examples (use these or invent fitting ones):
API Integration, ML/AI, DevOps, Finance, Web Dev, Data Engineering,
Security, Mobile, Design, Performance, Testing, Architecture

Effort guidelines:
- Quick (<1hr): read a doc, run a single command, trivial code change
- 1-2hrs: implement a small feature, integrate an API with a few endpoints
- Half-day: build a full module, significant refactoring
- Multi-day: new major feature, research + implementation\
"""


def analyze_content(content: FetchedContent, model: str = "claude-sonnet-4-6") -> list[ExtractedTask]:
    client = anthropic.Anthropic()
    user_prompt = USER_PROMPT_TEMPLATE.format(
        source_type=content.source_type,
        url=content.url,
        title=content.title,
        body=content.body,
    )

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # One-shot retry with correction
        retry_response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": raw_text},
                {
                    "role": "user",
                    "content": "Your previous response was not valid JSON. Return only the JSON object, nothing else.",
                },
            ],
        )
        data = json.loads(retry_response.content[0].text)

    return [
        ExtractedTask(
            title=t["title"],
            description=t["description"],
            priority=t["priority"],
            categories=t.get("categories", []),
            effort=t["effort"],
            source_url=content.url,
            source_type=content.source_type,
            raw_claude_json=t,
        )
        for t in data["tasks"]
    ]
