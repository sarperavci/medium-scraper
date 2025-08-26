import asyncio
from medium_scraper import DecodoScraperRequestSender, MediumMarkdownParser, CachedRequestSender, RequestsRequestSender 


async def main() -> None:
    url = "https://medium.com/@sarperavci/two-million-hackthebox-write-up-7433944c2efa"
   # inner = DecodoScraperRequestSender(api_key="<api_key>")
    inner = RequestsRequestSender()
    sender = CachedRequestSender(inner, db_path="cache.db")
    resp = await sender.fetch(url)
    parser = MediumMarkdownParser()
    result = parser.parse_html(resp.text, source_url=resp.url)
    if result.error:
        print(result.message or "Parse error")
        return
    print(result.title)
    print()
    print(result.markdown)


if __name__ == "__main__":
    asyncio.run(main()) 