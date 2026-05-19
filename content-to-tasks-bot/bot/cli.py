import argparse
import json
import os
import sys

from dotenv import load_dotenv

from bot.analyzer import analyze_content
from bot.fetchers import get_fetcher
from bot.models import ExtractedTask
from bot.notion_writer import create_tasks_batch


def main() -> None:
    load_dotenv()
    args = _parse_args()
    _validate_env(args)

    all_tasks: list[ExtractedTask] = []

    for url in args.urls:
        print(f"\nProcessing: {url}")

        fetcher = get_fetcher(url)
        content = fetcher.fetch(url)

        if content.fetch_method == "manual_fallback":
            pasted = _prompt_manual_content(url, content.source_type)
            if not pasted.strip():
                print(f"  Skipping — no content provided.")
                continue
            content.body = pasted
            content.fetch_method = "manual"

        if not content.body.strip():
            print(f"  Skipping — could not extract any content.")
            continue

        if args.verbose:
            print(f"  Source type : {content.source_type}")
            print(f"  Fetch method: {content.fetch_method}")
            print(f"  Body length : {len(content.body)} chars")

        tasks = analyze_content(content, model=args.model)
        print(f"  Extracted {len(tasks)} task(s)")
        all_tasks.extend(tasks)

        if args.output in ("json", "both") or args.dry_run:
            for task in tasks:
                _print_task(task)

        if args.output in ("notion", "both") and not args.dry_run:
            db_id = args.database_id or os.environ["NOTION_DATABASE_ID"]
            notion_token = os.environ["NOTION_API_TOKEN"]
            page_urls = create_tasks_batch(db_id, tasks, notion_token)
            for task, page_url in zip(tasks, page_urls):
                print(f"    + [{task.priority}] {task.title}")
                print(f"      {page_url}")

    print(f"\nDone. {len(all_tasks)} total task(s) processed.")

    if args.output == "json" or args.dry_run:
        _dump_json(all_tasks)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bot",
        description="Turn web/social content into Notion tasks using Claude AI.",
    )
    parser.add_argument("urls", nargs="+", metavar="URL", help="One or more URLs to process")
    parser.add_argument("--dry-run", action="store_true", help="Analyze and print tasks; do not write to Notion")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print fetch details and raw output")
    parser.add_argument(
        "--output",
        choices=("notion", "json", "both"),
        default="notion",
        help="Where to send results (default: notion)",
    )
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Claude model ID")
    parser.add_argument("--database-id", default=None, help="Override NOTION_DATABASE_ID env var")
    return parser.parse_args()


def _validate_env(args: argparse.Namespace) -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Error: ANTHROPIC_API_KEY is not set. Add it to your .env file.")
    if args.output in ("notion", "both") and not args.dry_run:
        if not os.environ.get("NOTION_API_TOKEN"):
            sys.exit("Error: NOTION_API_TOKEN is not set. Add it to your .env file.")
        if not args.database_id and not os.environ.get("NOTION_DATABASE_ID"):
            sys.exit(
                "Error: NOTION_DATABASE_ID is not set. Add it to your .env file or use --database-id."
            )


def _prompt_manual_content(url: str, source_type: str) -> str:
    print(f"\n  [{source_type.capitalize()} content cannot be fetched automatically]")
    print(f"  Paste the content below. Press Enter twice then Ctrl+D (or Ctrl+Z on Windows) when done:")
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


def _print_task(task: ExtractedTask) -> None:
    print(f"\n  [{task.priority}] {task.title}")
    print(f"  Effort    : {task.effort}")
    print(f"  Categories: {', '.join(task.categories)}")
    print(f"  {task.description}")


def _dump_json(tasks: list[ExtractedTask]) -> None:
    output = [
        {
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "categories": t.categories,
            "effort": t.effort,
            "source_url": t.source_url,
            "source_type": t.source_type,
        }
        for t in tasks
    ]
    print("\n--- JSON OUTPUT ---")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
