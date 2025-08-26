# Library

Async tools for exploring Medium tag archives and converting posts to Markdown.

## Modules at a glance

- `medium_scraper.request_sender.*` → pluggable HTTP backends
- `medium_scraper.explorer.medium_explorer.MediumExplorer` → tag pagination via GraphQL
- `medium_scraper.parser.medium_parser.MediumMarkdownParser` → HTML→Markdown
- `medium_scraper.concurrent` → bulk fetch/scrape helpers
- `medium_scraper.models` → data models

## Installation

```bash
pip install -e .
```

## Request backends

### RequestsRequestSender

Direct HTTP with realistic Chrome-like headers and optional proxies.

```python
from medium_scraper import RequestsRequestSender

sender = RequestsRequestSender(
    proxies=["http://user:pass@ip1:port", "http://user:pass@ip2:port"],
    timeout=30.0,
)
resp = await sender.fetch("https://medium.com/tag/tryhackme")
```

### DecodoScraperRequestSender

Routes requests through Decodo Scraper API.

```python
from medium_scraper import DecodoScraperRequestSender

sender = DecodoScraperRequestSender(api_key="<DECODO_API_KEY>", advanced=False)
resp = await sender.fetch("https://medium.com/@user/post")
```

- `advanced=True` enables headless rendering for sites that require it.
- Provide `api_key` as the raw token or `Basic <token>`.

### CachedRequestSender

Wraps any backend and stores 200 responses in a SQLite DB.

```python
from medium_scraper import CachedRequestSender, RequestsRequestSender

inner = RequestsRequestSender()
cached = CachedRequestSender(inner, db_path="cache.db", default_ttl_seconds=None)
resp = await cached.fetch("https://medium.com/tag/python")
```

- Only status 200 responses are cached
- TTL can be provided per-call: `await cached.request("GET", url, ttl_seconds=3600)`

## Explorer (GraphQL pagination)

```python
from medium_scraper import MediumExplorer, RequestsRequestSender

explorer = MediumExplorer(RequestsRequestSender())
items = await explorer.get_articles_by_category("tryhackme", year=2024, month=6, page_size=50)
for a in items:
    print(a.date, a.title, a.url)
```

Each `Article` contains: `post_id`, `title`, `author`, `date`, `category`, `url`.

## HTML → Markdown parsing

```python
from medium_scraper import MediumMarkdownParser

parser = MediumMarkdownParser()
parsed = parser.parse_html(html_string, source_url="https://medium.com/@user/post")
if parsed.error:
    print(parsed.message)
else:
    print(parsed.title)
    print(parsed.markdown)
```

The converter supports:

- Code blocks and line breaks
- Images (`<figure>`, `<picture>`, `<img>`) with best-source selection
- Links normalized to absolute Medium URLs when needed
- Iframes preserved as raw HTML
- Post-processing to normalize Markdown fences and reduce noise

## Concurrency helpers

- `fetch_all(urls, sender, concurrency=10, ...)` → list of dicts with `text`, `status_code`, etc.
- `scrape_markdown_all(urls, sender, concurrency=10, ...)` → list with `ok`, `title`, `markdown`.

```python
from medium_scraper import RequestsRequestSender, scrape_markdown_all

urls = ["https://medium.com/@user/post1", "https://medium.com/@user/post2"]
results = await scrape_markdown_all(urls, RequestsRequestSender(), concurrency=10)
```

## Models

```python
from medium_scraper import ArticleParseResult, HttpResponse
```

- `HttpResponse(url: str, status_code: int, headers: Dict[str, str], text: str)`
- `ArticleParseResult.success(markdown, title)` / `.failure(message)`

## Error handling

- Network errors raise exceptions from the underlying backend; catch around `await sender.fetch(...)`.
- Markdown parsing returns `ArticleParseResult` with `error=True` and a message; no exception is raised by default.

## Tips

- Use caching for bulk operations or flaky networks
- Try Decodo with `advanced=True` when pages are empty due to client-side rendering
- Provide rotating proxies for the Requests backend to reduce blocks 