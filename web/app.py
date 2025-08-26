from __future__ import annotations

import asyncio
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from zipfile import ZipFile, ZIP_DEFLATED
import sqlite3
import time
import uuid
from datetime import datetime, date

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from medium_scraper import (
    CachedRequestSender,
    DecodoScraperRequestSender,
    MediumExplorer,
    RequestsRequestSender,
    scrape_markdown_all,
    ProgressBar,
    StatTracker,
)

app = FastAPI(title="Decodo Medium Scraper API", version="0.1.0")

# WebSocket connection manager for progress tracking
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        self.active_connections[job_id] = websocket

    def disconnect(self, job_id: str):
        if job_id in self.active_connections:
            del self.active_connections[job_id]

    async def send_progress(self, job_id: str, progress_data: Dict[str, Any]):
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_json(progress_data)
            except Exception:
                self.disconnect(job_id)

manager = ConnectionManager()

STATIC_DIR = Path(__file__).resolve().parent  / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "app.db"

def _db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at REAL NOT NULL,
            input_json TEXT NOT NULL,
            output_json TEXT,
            error TEXT
        );
        """
    )
    return conn

def _job_insert(job_type: str, payload: Dict[str, Any]) -> str:
    conn = _db_conn()
    jid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO jobs (id, job_type, status, created_at, input_json) VALUES (?, ?, ?, ?, ?)",
        (jid, job_type, "pending", time.time(), json.dumps(payload, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    return jid

def _job_update(jid: str, *, status: Optional[str] = None, output: Optional[Any] = None, error: Optional[str] = None, progress: Optional[Dict[str, Any]] = None) -> None:
    conn = _db_conn()
    if status is not None and output is not None and error is not None:
        conn.execute("UPDATE jobs SET status=?, output_json=?, error=? WHERE id=?", (status, json.dumps(output, ensure_ascii=False), error, jid))
    elif status is not None and output is not None:
        conn.execute("UPDATE jobs SET status=?, output_json=? WHERE id=?", (status, json.dumps(output, ensure_ascii=False), jid))
    elif status is not None and error is not None:
        conn.execute("UPDATE jobs SET status=?, error=? WHERE id=?", (status, error, jid))
    elif status is not None:
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, jid))
    conn.commit()
    conn.close()
    
    # Send progress update via WebSocket if available
    if progress is not None:
        asyncio.create_task(manager.send_progress(jid, progress))

def _job_get(jid: str) -> Optional[Dict[str, Any]]:
    conn = _db_conn()
    cur = conn.execute("SELECT id, job_type, status, created_at, input_json, output_json, error FROM jobs WHERE id=?", (jid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "job_type": row[1],
        "status": row[2],
        "created_at": row[3],
        "input": json.loads(row[4]) if row[4] else None,
        "output": json.loads(row[5]) if row[5] else None,
        "error": row[6],
    }

def _job_list(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _db_conn()
    cur = conn.execute("SELECT id, job_type, status, created_at FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "job_type": r[1], "status": r[2], "created_at": r[3]}
        for r in rows
    ]
    
def _pd(s: str) -> date:
    if str(s).lower() in {"today", "now"}: return date.today()
    return datetime.strptime(str(s), "%Y-%m-%d").date()

@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    await manager.connect(websocket, job_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)

@app.get("/")
async def index() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Decodo Medium Scraper</h1>")


def _proxy_normalize(proxies_input: Optional[Any]) -> Optional[List[str]]:
    if proxies_input is None:
        return None
    # accepts JSON list[str] or newline-delimited string
    if isinstance(proxies_input, list):
        return [str(p).strip() for p in proxies_input if str(p).strip()]
    if isinstance(proxies_input, str):
        try:
            obj = json.loads(proxies_input)
            if isinstance(obj, list):
                return [str(p).strip() for p in obj if str(p).strip()]
        except Exception:
            pass
        return [ln.strip() for ln in proxies_input.splitlines() if ln.strip()]
    return None


def _build_sender(opts: Dict[str, Any]):
    sender_name = (opts.get("sender") or "auto").lower()
    decodo_api_key = opts.get("decodo_api_key")
    advanced = bool(opts.get("advanced", False))
    timeout = float(opts.get("timeout", 30.0))
    cache_db = str(opts.get("cache_db") or "cache.db")
    proxies_list = _proxy_normalize(opts.get("proxies"))
    is_cache_disabled = bool(opts.get("disable_cache", False))

    if sender_name == "decodo" or (sender_name == "auto" and decodo_api_key):
        if not decodo_api_key:
            raise ValueError("decodo_api_key required for sender=decodo")
        inner = DecodoScraperRequestSender(api_key=decodo_api_key, advanced=advanced, timeout=timeout)
    else:
        inner = RequestsRequestSender(proxies=proxies_list, timeout=timeout)
    if is_cache_disabled:
        return inner
    return CachedRequestSender(inner, db_path=cache_db)


@app.post("/api/paginate")
async def api_paginate(payload: Dict[str, Any]) -> JSONResponse:
    tag = payload.get("tag")
    year = payload.get("year")
    month = payload.get("month")
    from_date = payload.get("from_date")
    to_date = payload.get("to_date")
    if not tag:
        raise HTTPException(status_code=400, detail="tag is required")
    page_size = int(payload.get("page_size", 50))

    sender = _build_sender(payload)
    explorer = MediumExplorer(sender)
    results: List[Dict[str, Any]] = []

    # range mode
    if from_date and to_date:
        try:
            start = _pd(from_date)
            end = _pd(to_date)
            ym = []
            y, m = start.year, start.month
            while (y, m) <= (end.year, end.month):
                ym.append((y, m))
                if m == 12: y, m = y + 1, 1
                else: m += 1
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid from_date/to_date")
        for y, m in ym:
            items = await explorer.get_articles_by_category(tag, year=y, month=m, page_size=page_size)
            results.extend([it.__dict__ for it in items])
    else:
        if year is None or month is None:
            raise HTTPException(status_code=400, detail="Provide year/month or from_date/to_date")
        items = await explorer.get_articles_by_category(tag, year=int(year), month=int(month), page_size=page_size)
        results.extend([it.__dict__ for it in items])

    return JSONResponse(results)


def _extract_urls(urls_input: Any) -> List[str]:
    urls: List[str] = []
    if isinstance(urls_input, list):
        for u in urls_input:
            if isinstance(u, str) and u.strip():
                urls.append(u.strip())
    elif isinstance(urls_input, str):
        # try JSON list or list[dict]
        try:
            obj = json.loads(urls_input)
            if isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict) and item.get("url"):
                        urls.append(str(item["url"]))
                    elif isinstance(item, str) and item.strip():
                        urls.append(item.strip())
        except Exception:
            # fallback to newline-delimited
            urls = [ln.strip() for ln in urls_input.splitlines() if ln.strip()]
    return urls


@app.post("/api/scrape")
async def api_scrape(payload: Dict[str, Any]) -> JSONResponse:
    urls_input = payload.get("urls") or payload.get("urls_file") or payload.get("urls_text")
    urls = _extract_urls(urls_input or [])
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    sender = _build_sender(payload)
    concurrency = int(payload.get("concurrency", 10))
    results = await scrape_markdown_all(urls, sender, concurrency=concurrency)
    return JSONResponse(results)


@app.post("/api/scrape-zip")
async def api_scrape_zip(payload: Dict[str, Any]) -> StreamingResponse:
    urls_input = payload.get("urls") or payload.get("urls_file") or payload.get("urls_text")
    urls = _extract_urls(urls_input or [])
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    sender = _build_sender(payload)
    concurrency = int(payload.get("concurrency", 10))
    results = await scrape_markdown_all(urls, sender, concurrency=concurrency)

    def stream_zip():
        buf = io.BytesIO()
        with ZipFile(buf, mode="w", compression=ZIP_DEFLATED) as zf:
            manifest = []
            for res in results:
                manifest.append(res)
                if res.get("ok"):
                    title = str(res.get("title") or "article").strip()
                    slug = title.lower().replace(" ", "-")[:80] or "article"
                    zf.writestr(f"{slug}.md", res.get("markdown", ""))
                if buf.tell() > 1_000_000:
                    zf.fp.flush()
                    buf.seek(0)
                    chunk = buf.read()
                    buf.truncate(0)
                    buf.seek(0)
                    yield chunk
            zf.writestr("results.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        buf.seek(0)
        yield buf.read()

    headers = {"Content-Disposition": "attachment; filename=scrape_results.zip"}
    return StreamingResponse(stream_zip(), media_type="application/zip", headers=headers)


@app.get("/api/jobs")
async def api_jobs() -> JSONResponse:
    return JSONResponse(_job_list(100))

@app.get("/api/jobs/{job_id}")
async def api_job_detail(job_id: str) -> JSONResponse:
    job = _job_get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(job)


@app.get("/api/jobs/{job_id}/zip")
async def api_job_zip(job_id: str) -> StreamingResponse:
    job = _job_get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["job_type"].startswith("scrape") is False:
        raise HTTPException(status_code=400, detail="ZIP available only for scrape jobs")
    results = job.get("output") or []
    buf = io.BytesIO()
    with ZipFile(buf, mode="w", compression=ZIP_DEFLATED) as zf:
        for res in results:
            if res.get("ok"):
                title = str(res.get("title") or "article").strip()
                slug = title.lower().replace(" ", "-")[:80] or "article"
                zf.writestr(f"{slug}.md", res.get("markdown", ""))
        zf.writestr("results.json", json.dumps(results, ensure_ascii=False, indent=2))
    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={job_id}.zip"}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)


async def _worker_paginate(job_id: str):
    job = _job_get(job_id)
    if not job:
        return
    payload = job["input"] or {}
    try:
        # Validate input parameters
        tag = payload.get("tag")
        year = payload.get("year")
        month = payload.get("month")
        
        if not tag:
            raise ValueError("Tag is required")
        if not year or not month:
            raise ValueError("Year and month are required")
        
        year = int(year)
        month = int(month)
        
        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12")
        if year < 2000 or year > 2030:
            raise ValueError("Year must be between 2000 and 2030")
        
        print(f"Paginate job {job_id}: Getting articles for tag '{tag}' in {year}-{month:02d}")
        
        sender = _build_sender(payload)
        explorer = MediumExplorer(sender)
        items = await explorer.get_articles_by_category(tag, year=year, month=month)
        _job_update(job_id, status="done", output=[it.__dict__ for it in items])
        print(f"Paginate job {job_id}: Found {len(items)} articles")
    except Exception as exc:
        import traceback
        error_msg = str(exc) if str(exc) else f"{type(exc).__name__}: {repr(exc)}"
        if not error_msg.strip():
            error_msg = f"Unknown error of type {type(exc).__name__}. Traceback: {traceback.format_exc()}"
        print(f"Paginate job {job_id} failed: {error_msg}")
        _job_update(job_id, status="error", error=error_msg)


async def _worker_scrape(job_id: str):
    job = _job_get(job_id)
    if not job:
        return
    payload = job["input"] or {}
    try:
        sender = _build_sender(payload)
        urls = _extract_urls(payload.get("urls") or payload.get("urls_text") or [])
        
        # Create progress callback for WebSocket updates
        def progress_callback(completed: int, total: int, percentage: float, stats: Dict[str, Any]):
            progress_data = {
                "type": "progress",
                "completed": completed,
                "total": total,
                "percentage": percentage,
                "stats": stats,
                "current_url": stats.get("current_url", ""),
                "success_count": stats.get("success", 0),
                "failed_count": stats.get("failed", 0),
                "parse_failed_count": stats.get("parse_failed", 0)
            }
            _job_update(job_id, progress=progress_data)
        
        results = await scrape_markdown_all(
            urls, 
            sender, 
            concurrency=int(payload.get("concurrency", 10)),
            progress_callback=progress_callback
        )
        _job_update(job_id, status="done", output=results)
    except Exception as exc:
        import traceback
        error_msg = str(exc) if str(exc) else f"{type(exc).__name__}: {repr(exc)}"
        if not error_msg.strip():
            error_msg = f"Unknown error of type {type(exc).__name__}. Traceback: {traceback.format_exc()}"
        print(f"Scrape job {job_id} failed: {error_msg}")
        _job_update(job_id, status="error", error=error_msg)


@app.post("/api/jobs/paginate")
async def api_jobs_paginate(payload: Dict[str, Any]) -> JSONResponse:
    required = all(k in payload for k in ("tag", "year", "month"))
    if not required:
        raise HTTPException(status_code=400, detail="tag, year, month are required")
    jid = _job_insert("paginate", payload)
    _job_update(jid, status="running")
    asyncio.create_task(_worker_paginate(jid))
    return JSONResponse({"id": jid, "status": "running"})


@app.post("/api/jobs/scrape")
async def api_jobs_scrape(payload: Dict[str, Any]) -> JSONResponse:
    urls = _extract_urls(payload.get("urls") or payload.get("urls_text") or [])
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    jid = _job_insert("scrape", payload)
    _job_update(jid, status="running")
    asyncio.create_task(_worker_scrape(jid))
    return JSONResponse({"id": jid, "status": "running"}) 