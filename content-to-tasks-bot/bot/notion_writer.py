import time

from notion_client import Client
from notion_client.errors import APIResponseError

from bot.models import ExtractedTask


def create_tasks_batch(db_id: str, tasks: list[ExtractedTask], notion_token: str) -> list[str]:
    notion = Client(auth=notion_token)
    urls = []
    for task in tasks:
        url = _create_page_with_retry(notion, db_id, task)
        urls.append(url)
        time.sleep(0.4)  # stay under Notion's 3 req/s limit
    return urls


def _create_page_with_retry(notion: Client, db_id: str, task: ExtractedTask) -> str:
    backoff = 1
    for attempt in range(4):
        try:
            response = notion.pages.create(
                parent={"database_id": db_id},
                properties=_build_properties(task),
            )
            return response["url"]
        except APIResponseError as e:
            if e.status == 429 and attempt < 3:
                time.sleep(backoff)
                backoff *= 2
            else:
                raise


def _build_properties(task: ExtractedTask) -> dict:
    return {
        "Name": {
            "title": [{"text": {"content": task.title}}]
        },
        "Description": {
            "rich_text": [{"text": {"content": task.description}}]
        },
        "Priority": {
            "select": {"name": task.priority}
        },
        "Category": {
            "multi_select": [{"name": c} for c in task.categories]
        },
        "Effort": {
            "select": {"name": task.effort}
        },
        "Source URL": {
            "url": task.source_url
        },
        "Source Type": {
            "select": {"name": task.source_type}
        },
    }
