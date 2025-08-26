# Medium Scraper Web Interface

Web interface for the medium-scraper library providing an easy-to-use GUI for scraping Medium articles.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

Then open your browser to `http://localhost:8000`

## Docker

```bash
docker build -t medium-scraper-web .
docker run -p 8000:8000 medium-scraper-web
```

## Features

- Interactive web interface for Medium scraping
- Real-time progress tracking via WebSocket
- Download scraped articles as ZIP files
- Support for multiple request senders (Direct requests, Decodo Scraper)
- Persistent job history and caching 