from __future__ import annotations

import asyncio
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich import print
from rich.progress import Progress

from medium_scraper import (
    CachedRequestSender,
    DecodoScraperRequestSender,
    MediumExplorer,
    scrape_markdown_all,
    RequestsRequestSender,
)

app = typer.Typer(
    name="Decodo Medium Scraper & Markdown Generator",
    add_completion=False,
    help=(
        "Async Medium scraper that paginates tags and generates Markdown from articles, "
        "using either Decodo (Core/Advanced) or direct requests. Supports concurrency, "
        "persistent caching and optional proxies."
    ),
)


def _load_proxies(proxies_path: Optional[str]):
    if not proxies_path:
        return None
    p = Path(proxies_path)
    if not p.exists():
        raise typer.BadParameter(f"Proxies file not found: {proxies_path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data
    except Exception as exc:
        raise typer.BadParameter(f"Invalid proxies file (expect JSON dict or list[dict]): {exc}")


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\-\_\s]+", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"\-+", "-", text)
    return text or "article"


def _sender_from_opts(
    sender: str,
    decodo_api_key: Optional[str],
    advanced: bool,
    proxies,
    cache_db: Optional[str],
    timeout: float,
):
    sender = (sender or "auto").lower()
    if sender not in {"auto", "requests", "decodo"}:
        raise typer.BadParameter("--sender must be one of: auto, requests, decodo")

    inner = None
    if sender == "decodo" or (sender == "auto" and decodo_api_key):
        if not decodo_api_key:
            raise typer.BadParameter("--decodo-api-key is required when --sender=decodo")
        inner = DecodoScraperRequestSender(api_key=decodo_api_key, advanced=advanced, timeout=timeout)
    else:
        inner = RequestsRequestSender(proxies=proxies, timeout=timeout)

    return CachedRequestSender(inner, db_path=cache_db or "cache.db")


def _parse_date(s: str) -> date:
    if s.lower() in {"today", "now"}:
        return date.today()
    return datetime.strptime(s, "%Y-%m-%d").date()


def _month_iter(start: date, end: date) -> List[Tuple[int, int]]:
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return months


@app.command()
def paginate(
    tag: str = typer.Argument(..., help="Medium tag slug (e.g., tryhackme)"),
    year: Optional[int] = typer.Option(None, help="Target year (e.g., 2022)"),
    month: Optional[int] = typer.Option(None, help="Target month (1-12)"),
    page_size: int = typer.Option(50, help="Number of posts per request"),
    sender: str = typer.Option("auto", help="Request backend: auto | requests | decodo"),
    decodo_api_key: Optional[str] = typer.Option(None, envvar="DECODO_API_KEY", help="Decodo API key (required if --sender=decodo)"),
    advanced: bool = typer.Option(False, help="Decodo Advanced plan (adds headless rendering)"),
    proxies_path: Optional[str] = typer.Option(None, help="Path to JSON proxies (dict or list[dict]); used only for requests sender"),
    cache_db: Optional[str] = typer.Option("cache.db", help="SQLite cache DB path (persistent between runs)"),
    timeout: float = typer.Option(30.0, help="Request timeout in seconds"),
    output: Optional[str] = typer.Option(None, help="Output JSON file; prints to stdout if omitted"),
    from_date: Optional[str] = typer.Option(None, help="Start date YYYY-MM-DD or 'today'"),
    to_date: Optional[str] = typer.Option(None, help="End date YYYY-MM-DD or 'today'"),
):
    """List articles for a tag as JSON (single month or date range)."""
    if (year is None or month is None) and (not from_date or not to_date):
        raise typer.BadParameter("Provide --year and --month, or --from-date and --to-date")

    proxies = _load_proxies(proxies_path)
    client = _sender_from_opts(sender, decodo_api_key, advanced, proxies, cache_db, timeout)

    async def _run():
        explorer = MediumExplorer(client)
        results = []
        if from_date and to_date:
            start = _parse_date(from_date)
            end = _parse_date(to_date)
            ym_list = _month_iter(start, end)
            with Progress() as progress:
                task = progress.add_task("Fetching feed (range)...", total=len(ym_list))
                for y, m in ym_list:
                    items = await explorer.get_articles_by_category(tag, year=y, month=m, page_size=page_size)
                    results.extend(items)
                    progress.advance(task)
        else:
            with Progress() as progress:
                task = progress.add_task("Fetching feed...", total=None)
                items = await explorer.get_articles_by_category(tag, year=year or 0, month=month or 0, page_size=page_size)
                progress.update(task, completed=1)
                results.extend(items)

        data = [item.__dict__ for item in results]
        if output:
            Path(output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))

    asyncio.run(_run())


@app.command()
def scrape(
    urls_file: Optional[str] = typer.Option(None, help="Path to URLs input: either newline-delimited text of Medium URLs OR JSON produced by 'paginate' (list of articles with 'url' field)"),
    url: List[str] = typer.Argument(None, help="One or more Medium post URLs to scrape"),
    out_dir: str = typer.Option("out", help="Directory to write Markdown files and manifest"),
    concurrency: int = typer.Option(10, help="Maximum concurrent requests"),
    sender: str = typer.Option("auto", help="Request backend: auto | requests | decodo"),
    decodo_api_key: Optional[str] = typer.Option(None, envvar="DECODO_API_KEY", help="Decodo API key (required if --sender=decodo)"),
    advanced: bool = typer.Option(False, help="Decodo Advanced plan (adds headless rendering)"),
    proxies_path: Optional[str] = typer.Option(None, help="Path to proxies input: either JSON dict/list OR newline-delimited proxy URLs"),
    cache_db: Optional[str] = typer.Option("cache.db", help="SQLite cache DB path (persistent between runs)"),
    timeout: float = typer.Option(30.0, help="Request timeout in seconds"),
):
    """Scrape URLs and save Markdown files plus a results manifest (JSON)."""
    urls: List[str] = list(url)
    if urls_file:
        content = Path(urls_file).read_text(encoding="utf-8")
        loaded_urls: List[str] = []
        # Try JSON first
        try:
            obj = json.loads(content)
            if isinstance(obj, list):
                # paginate output: list of article dicts with 'url' key
                for item in obj:
                    if isinstance(item, dict) and item.get("url"):
                        loaded_urls.append(str(item["url"]))
                # or a plain list of URL strings
                if not loaded_urls:
                    for item in obj:
                        if isinstance(item, str) and item.strip():
                            loaded_urls.append(item.strip())
        except Exception:
            # Fallback to text file with newline-delimited URLs
            loaded_urls = [line.strip() for line in content.splitlines() if line.strip()]
        urls += loaded_urls
    if not urls:
        raise typer.BadParameter("No URLs provided. Provide arguments or --urls-file.")

    # Proxies: allow JSON dict/list or newline-delimited proxy URLs; normalize in sender
    proxies = None
    if proxies_path:
        ptext = Path(proxies_path).read_text(encoding="utf-8")
        try:
            proxies = json.loads(ptext)
        except Exception:
            lines = [ln.strip() for ln in ptext.splitlines() if ln.strip()]
            proxies = lines

    client = _sender_from_opts(sender, decodo_api_key, advanced, proxies, cache_db, timeout)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    async def _run():
        results = await scrape_markdown_all(urls, client, concurrency=concurrency)
        manifest = []
        for res in results:
            if res.get("ok"):
                url_val = res["url"]
                slug = _slugify(url_val.rsplit("/", 1)[-1])
                if not slug or slug == "article":
                    slug = _slugify(res.get("title") or "article")
                filename = f"{slug}.md"
                (out_path / filename).write_text(res["markdown"], encoding="utf-8")
                res["file"] = filename
            manifest.append(res)
        (out_path / "results.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(results)} results to {out_path}")

    asyncio.run(_run())


@app.command("scrape-tag")
def scrape_tag(
    tag: str = typer.Argument(..., help="Medium tag slug (e.g., tryhackme)"),
    year: Optional[int] = typer.Option(None, help="Target year (e.g., 2022)"),
    month: Optional[int] = typer.Option(None, help="Target month (1-12)"),
    page_size: int = typer.Option(50, help="Number of posts per request"),
    out_dir: str = typer.Option("out", help="Directory to write Markdown files and manifest"),
    concurrency: int = typer.Option(10, help="Maximum concurrent requests"),
    sender: str = typer.Option("auto", help="Request backend: auto | requests | decodo"),
    decodo_api_key: Optional[str] = typer.Option(None, envvar="DECODO_API_KEY", help="Decodo API key (required if --sender=decodo)"),
    advanced: bool = typer.Option(False, help="Decodo Advanced plan (adds headless rendering)"),
    proxies_path: Optional[str] = typer.Option(None, help="Path to JSON proxies (dict or list[dict]); used only for requests sender"),
    cache_db: Optional[str] = typer.Option("cache.db", help="SQLite cache DB path (persistent between runs)"),
    timeout: float = typer.Option(30.0, help="Request timeout in seconds"),
    from_date: Optional[str] = typer.Option(None, help="Start date YYYY-MM-DD or 'today'"),
    to_date: Optional[str] = typer.Option(None, help="End date YYYY-MM-DD or 'today'"),
):
    """Paginate a tag (single month or date range) and scrape all posts to Markdown."""
    if (year is None or month is None) and (not from_date or not to_date):
        raise typer.BadParameter("Provide --year and --month, or --from-date and --to-date")

    proxies = _load_proxies(proxies_path)
    client = _sender_from_opts(sender, decodo_api_key, advanced, proxies, cache_db, timeout)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    async def _run():
        explorer = MediumExplorer(client)
        urls: List[str] = []
        if from_date and to_date:
            start = _parse_date(from_date)
            end = _parse_date(to_date)
            ym_list = _month_iter(start, end)
            with Progress() as progress:
                t1 = progress.add_task("Fetching feed (range)...", total=len(ym_list))
                for y, m in ym_list:
                    items = await explorer.get_articles_by_category(tag, year=y, month=m, page_size=page_size)
                    urls.extend([a.url for a in items if a.url])
                    progress.advance(t1)
        else:
            with Progress() as progress:
                t1 = progress.add_task("Fetching feed...", total=None)
                items = await explorer.get_articles_by_category(tag, year=year or 0, month=month or 0, page_size=page_size)
                progress.update(t1, completed=1)
                urls.extend([a.url for a in items if a.url])

        if not urls:
            print("[yellow]No URLs found[/yellow]")
            return

        with Progress() as progress:
            t2 = progress.add_task("Scraping articles...", total=len(urls))
            results = await scrape_markdown_all(urls, client, concurrency=concurrency)
            progress.update(t2, completed=len(urls))
        manifest = []
        for res in results:
            if res.get("ok"):
                url_val = res["url"]
                slug = _slugify(url_val.rsplit("/", 1)[-1])
                if not slug or slug == "article":
                    slug = _slugify(res.get("title") or "article")
                filename = f"{slug}.md"
                (out_path / filename).write_text(res["markdown"], encoding="utf-8")
                res["file"] = filename
            manifest.append(res)
        (out_path / "results.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(results)} results to {out_path}")

    asyncio.run(_run())


if __name__ == "__main__":
    app() 