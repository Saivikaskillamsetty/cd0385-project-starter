# content-to-tasks-bot

A CLI bot that turns social media and web content into actionable Notion tasks using Claude AI.

Share a tweet, YouTube video, Instagram reel, or any article — the bot extracts concrete TODO items and creates them in your Notion database, ready to prioritize and act on.

## How it works

1. You provide one or more URLs (tweets, reels, YouTube, articles)
2. The bot fetches the content (or prompts you to paste it for platforms that block scraping)
3. Claude analyzes the content and extracts 1–8 actionable developer tasks
4. Tasks are created in your Notion database with priority, effort, categories, and a link back to the source

## Setup

### 1. Clone and install

```bash
git clone https://github.com/saivikaskillamsetty/content-to-tasks-bot.git
cd content-to-tasks-bot
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

| Variable | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `NOTION_API_TOKEN` | [notion.so/my-integrations](https://www.notion.so/my-integrations) — create a new integration, copy the token |
| `NOTION_DATABASE_ID` | See below |

### 3. Create your Notion database

1. In Notion, create a new full-page database (table view)
2. Add these properties with the exact names and types:

| Property Name | Type |
|---|---|
| Name | Title (default) |
| Description | Text |
| Priority | Select — add options: `High`, `Medium`, `Low` |
| Category | Multi-select |
| Effort | Select — add options: `Quick (<1hr)`, `1-2hrs`, `Half-day`, `Multi-day` |
| Source URL | URL |
| Source Type | Select |
| Status | Status (built-in) |

3. Share the database with your integration: click the `...` menu → **Connections** → find your integration
4. Copy the database ID from the URL: `notion.so/<workspace>/**{DATABASE_ID}**?v=...`
5. Paste it into `.env` as `NOTION_DATABASE_ID`

### 4. (Optional) Instagram support

To fetch Instagram reels automatically, set `INSTAGRAM_BASIC_DISPLAY_TOKEN` in `.env`.  
Without it, the bot will prompt you to paste the caption manually.

## Usage

```bash
# Process a single URL
bot https://techcrunch.com/2025/05/some-article

# Multiple URLs at once
bot https://youtube.com/watch?v=abc123 https://x.com/user/status/123

# Preview tasks without writing to Notion
bot --dry-run https://example.com/article

# Output as JSON instead
bot --output json https://example.com/article

# Verbose mode (shows fetch details)
bot --verbose https://example.com/article
```

### All options

```
positional arguments:
  URL                   One or more URLs to process

options:
  --dry-run             Analyze and print tasks; do not write to Notion
  --verbose, -v         Print fetch details
  --output {notion,json,both}
                        Where to send results (default: notion)
  --model MODEL         Claude model ID (default: claude-sonnet-4-6)
  --database-id DB_ID   Override NOTION_DATABASE_ID env var
```

## Supported content types

| Source | Fetch method |
|---|---|
| Articles / blogs | Scraped (BeautifulSoup) |
| YouTube videos | Public oEmbed (no API key needed) |
| Tweets / X posts | Public oEmbed (no API key needed) |
| Instagram reels | oEmbed (requires token) or manual paste |

## Running tests

```bash
pytest tests/
```
