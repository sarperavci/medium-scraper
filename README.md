# Medium Scraper

A high-scale, async Medium scraper with request abstraction and HTML-to-Markdown parser. Quickly discover and convert Medium articles to clean Markdown with our intuitive web interface.

## 🌐 Web Interface (Recommended)

The easiest way to use Medium Scraper is through our web interface:

### Docker Deployment (Easiest Setup)

Pull our pre-built image from GitHub Container Registry:

```bash
docker run -p 8000:8000 ghcr.io/sarperavci/medium-scraper:latest
```

Then open your browser to `http://localhost:8000`

### Alternative Installation

```bash
# Install web dependencies  
pip install medium-scraper[web]

# Run web server
cd web && python app.py
```

### Features

- **Intuitive GUI** for scraping Medium articles
- **Real-time progress tracking** via WebSocket
- **Download results** as ZIP files
- **Job history** and persistent storage
- **Multiple request modes**:
  - **Decodo API**: Smart managed scraping (requires [Decodo API key](https://decodo.com))
  - **Custom Proxies**: Bring your own proxy list
  - **Proxyless**: Direct requests with your IP

## 🔧 Core Features

All components share these powerful features:

- **Async/await support** for high-performance operations
- **Multiple request backends**: Direct requests, custom proxies, or Decodo Scraper API
- **Intelligent caching** with configurable backends
- **Progress tracking** with callbacks
- **Concurrent processing** with rate limiting
- **Robust error handling** and retries

### Web Interface
- **Intuitive GUI** for scraping Medium articles
- **Real-time progress tracking** via WebSocket
- **Download results** as ZIP files
- **Job history** and persistent storage
- **Multiple request modes**:
  - **Decodo API**: Smart managed scraping (requires [Decodo API key](https://decodo.com))
  - **Custom Proxies**: Bring your own proxy list
  - **Proxyless**: Direct requests with your IP

### CLI Tool
- **Interactive prompts** with rich formatting
- **Progress bars** and detailed statistics  
- **Multiple output formats** (JSON, Markdown files)
- **Proxy support** and custom configurations
- **Tag pagination** and article filtering

### Core Library
These features are also available when using the library programmatically. See our [Library Documentation](docs/Library.md) for details.

## 📚 Library Usage

For programmatic usage of the core library, please refer to our [Library Documentation](docs/Library.md) which provides detailed examples.

## 🖥️ CLI Tool

The command-line interface offers powerful scraping capabilities. See our [CLI Documentation](docs/CLI.md) for comprehensive usage instructions.

## 🛠️ Installation Options

### Basic Installation
```bash
pip install medium-scraper
```


## 📚 Request Senders

The library supports multiple request backends:

1. **RequestsRequestSender**: Standard requests library (works with custom proxies or proxyless)
2. **DecodoScraperRequestSender**: Advanced scraping with [Decodo API](https://decodo.com) (requires API key)
3. **CachedRequestSender**: Adds caching to any sender

Choose the appropriate sender based on your needs:

```python
from medium_scraper import RequestsRequestSender, DecodoScraperRequestSender

# For simple use cases (proxyless or with custom proxies)
sender = RequestsRequestSender()

# For advanced scraping with Decodo (requires API key from https://decodo.com)
sender = DecodoScraperRequestSender(api_key="your-decodo-api-key")
```

## 🔄 Async Usage  

The library is designed to be fully async:

```python
import asyncio
from medium_scraper import MediumExplorer

async def main():
    explorer = MediumExplorer()
    articles = await explorer.get_tag_articles("python", limit=5)
    
    for article in articles:
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")

asyncio.run(main())
```


## 📖 Documentation

For more detailed information about each component, please see the documentation in the [docs](docs/) folder:

- [Library Documentation](docs/Library.md)
- [CLI Documentation](docs/CLI.md)  
- [Web Interface Documentation](docs/Web.md)

## 🔗 Links

- [PyPI Package](https://pypi.org/project/medium-scraper/)
- [GitHub Repository](https://github.com/sarperavci/medium-scraper)
- [Issue Tracker](https://github.com/sarperavci/medium-scraper/issues)