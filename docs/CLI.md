# CLI

Typer-based command line interface for pagination and Markdown scraping.

## Install runtime dependencies

```bash
pip install typer rich
```

Run the CLI:

```bash
python medium_scraper_cli.py --help
```

## Commands

### paginate

List articles under a tag archive for a given month or date range.

```bash
python medium_scraper_cli.py paginate TAG --year 2024 --month 6 --page-size 50
python medium_scraper_cli.py paginate TAG --from-date 2024-01-01 --to-date 2024-03-01 --output urls.json
```

Options:

- `--sender auto|requests|decodo` (default: auto)
- `--decodo-api-key <key>` or set `DECODO_API_KEY`
- `--advanced` (Decodo Advanced plan / headless)
- `--proxies-path /path/to/proxies.{json,txt}` (Requests backend only)
- `--cache-db cache.db` (SQLite cache path)
- `--timeout 30.0`
- `--output urls.json` (write results to file)

### scrape

Scrape one or more URLs and write Markdown files to a directory.

```bash
# From arguments
python medium_scraper_cli.py scrape --url https://medium.com/@user/post1 https://medium.com/@user/post2 --out-dir out/

# From a file (newline-delimited URLs OR JSON from paginate)
python medium_scraper_cli.py scrape --urls-file urls.json --out-dir out/
```

Options:

- `--concurrency 10`
- `--sender auto|requests|decodo`
- `--decodo-api-key <key>` / `--advanced`
- `--proxies-path /path/to/proxies.{json,txt}`
- `--cache-db cache.db`
- `--timeout 30.0`

### scrape-tag

End-to-end workflow: paginate a tag, then scrape every post to Markdown.

```bash
python medium_scraper_cli.py scrape-tag TAG --year 2024 --month 6 --out-dir out/
python medium_scraper_cli.py scrape-tag TAG --from-date 2024-01-01 --to-date 2024-02-01 --out-dir out/
```

## Proxies

For the Requests backend, supply proxies via JSON or a newline-delimited text file:

- JSON list: `["http://user:pass@ip:port", "http://user:pass@ip2:port"]`
- JSON dict or list of dicts compatible with `curl_cffi.requests` is also accepted by the CLI
- Plain text: one URL per line

## Output

- `paginate` prints JSON array of article objects (`url`, `title`, `date`, ...)
- `scrape` writes `*.md` files in `--out-dir` and a `results.json` manifest
- `scrape-tag` writes markdown for every discovered post and a `results.json` manifest

## Caching

- By default the CLI uses `cache.db` in the working directory
- Only status 200 responses are cached
- Clear cache by deleting the file

## Examples

```bash
# Use Decodo backend via env var
export DECODO_API_KEY=your_key
python medium_scraper_cli.py paginate tryhackme --year 2024 --month 6 --page-size 100

# Requests backend with proxies
python medium_scraper_cli.py scrape --url https://medium.com/@user/post1 --sender requests --proxies-path proxies.txt
``` 