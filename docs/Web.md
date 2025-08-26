# Web API (FastAPI)

HTTP interface for pagination and Markdown scraping.

## Install and run

```bash
pip install fastapi uvicorn
uvicorn medium_web.app:app --reload --port 8000
```

Visit: http://localhost:8000/

## Configuration

Payload fields common to all endpoints:

- `sender`: `auto` (default), `requests`, or `decodo`
- `decodo_api_key`: required for `sender=decodo` (or set `DECODO_API_KEY` in env)
- `advanced`: bool, Decodo Advanced/headless
- `timeout`: float seconds (default 30)
- `cache_db`: path to SQLite cache (default `cache.db`)
- `proxies`: list of proxy URLs or newline-delimited string (Requests backend)

## Endpoints

### POST /api/paginate

Discover posts for a tag and month or date range.

Request (month):

```json
{
  "tag": "tryhackme",
  "year": 2024,
  "month": 6,
  "page_size": 50,
  "sender": "auto"
}
```

Request (range):

```json
{
  "tag": "tryhackme",
  "from_date": "2024-01-01",
  "to_date": "2024-03-01",
  "page_size": 50
}
```

Response: JSON array of articles with `title`, `url`, `date`, etc.

### POST /api/scrape

Return Markdown for one or more URLs.

Request:

```json
{
  "urls": [
    "https://medium.com/@user/post1",
    "https://medium.com/@user/post2"
  ],
  "sender": "requests"
}
```

Response: list of results `[{ "url": ..., "ok": true, "title": ..., "markdown": ... }, ...]`.

### POST /api/scrape-zip

Like `/api/scrape` but streams a ZIP containing `*.md` files and `results.json`.

### Jobs endpoints

The server stores job history in `medium_web/data/app.db`.

- `GET /api/jobs` → latest jobs
- `GET /api/jobs/{id}` → job detail
- `GET /api/jobs/{id}/zip` → ZIP of Markdown for scrape jobs

### Worker endpoints (asynchronous jobs)

- `POST /api/jobs/paginate` with `{ "tag": ..., "year": ..., "month": ... }`
- `POST /api/jobs/scrape` with `{ "urls": [...] }`

The server schedules a background worker and returns `{ "id": <job_id>, "status": "running" }`.

## Examples

```bash
# Paginate
curl -s -X POST http://localhost:8000/api/paginate \
 -H 'content-type: application/json' \
 -d '{"tag":"tryhackme","year":2024,"month":6,"page_size":25}' | jq . | head

# Scrape
curl -s -X POST http://localhost:8000/api/scrape \
 -H 'content-type: application/json' \
 -d '{"urls":["https://medium.com/@user/post1"]}' | jq .

# Scrape as ZIP
curl -X POST http://localhost:8000/api/scrape-zip \
 -H 'content-type: application/json' \
 -d '{"urls":["https://medium.com/@user/post1","https://medium.com/@user/post2"]}' \
 --output results.zip
```

## Notes

- Use Decodo (`sender=decodo`) for pages that require JavaScript rendering
- Provide proxies via `proxies` for the Requests backend if you encounter blocks
- The default cache location is `cache.db` (server) and can be changed via payload `cache_db` 