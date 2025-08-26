# Medium Scraper

A free, high-scale, async Medium scraper with request abstraction and HTML-to-Markdown parser. Quickly discover and convert Medium articles to clean Markdown with our intuitive web interface.

<img width="1047" height="778" alt="Screenshot from 2025-08-26 16-04-20" src="https://github.com/user-attachments/assets/a6d7f310-0595-4e4c-b1ef-bca26cd84520" />


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

## 🚀 Usage

### Setting up Decodo API

[Decodo](https://visit.decodo.com/7a7O7A) provides a powerful API for scraping Medium articles. Our web interface supports this API out of the box.

To use the Decodo API, you need to get an API key from Decodo. Sign up and get your API key from [Decodo](https://visit.decodo.com/7a7O7A).

Once you have your API key, you can set it in the web interface by clicking the "Advanced Settings", set the `Sender` to `decodo-webscraping-api` and paste your API key in the `Decodo API Key` field.

<img width="1045" height="306" alt="Screenshot from 2025-08-26 16-16-43" src="https://github.com/user-attachments/assets/dd384660-299c-4ec5-b692-c005f51c85b3" />

### Setting up Custom Proxies

You can set up custom proxies in the web interface by clicking the "Advanced Settings", set the `Sender` to `requests` and paste your proxy list in the `Proxies` field.

### Setting up Proxyless

You can set up proxyless in the web interface by clicking the "Advanced Settings", set the `Sender` to `requests` and leave the `Proxies` field empty.


### Features

- **Intuitive GUI** for scraping Medium articles
- **Real-time progress tracking** via WebSocket
- **Download results** as ZIP files
- **Job history** and persistent storage
- **Multiple request modes**:
  - **Decodo API**: Smart managed scraping (requires [Decodo API key](visit.decodo.com/7a7O7A))
  - **Custom Proxies**: Bring your own proxy list
  - **Proxyless**: Direct requests with your IP


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
2. **DecodoScraperRequestSender**: Advanced scraping with [Decodo API](https://visit.decodo.com/7a7O7A) (requires API key)
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
