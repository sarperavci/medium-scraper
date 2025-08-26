import asyncio
from medium_scraper import RequestsRequestSender, MediumExplorer


async def main() -> None:
    sender = RequestsRequestSender()
    explorer = MediumExplorer(sender)
    articles = await explorer.get_articles_by_category("tryhackme", year=2022, month=2, page_size=50)
    print(f"Fetched {len(articles)} articles")
    for a in articles[:5]:
        print(f"- {a.date} | {a.title} | {a.url}")


if __name__ == "__main__":
    asyncio.run(main()) 