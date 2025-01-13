import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from tqdm import tqdm

MAIN_URL = "http://books.toscrape.com"
OUTPUT_FILE = "books_data.json"

async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        return await response.text()

async def get_category_links(session: aiohttp.ClientSession) -> list:
    html = await fetch_page(session, MAIN_URL)
    soup = BeautifulSoup(html, "html.parser")
    category_links = soup.select("div.side_categories ul > li > ul > li > a")
    return [f'{MAIN_URL}/{a["href"]}' for a in category_links]

async def get_book_links(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    book_links = []
    for a in soup.select("h3 a"):
        book_url = a["href"].replace("../../../", "")
        book_links.append(f'{MAIN_URL}/catalogue/{book_url}')
    return book_links

async def read_page(session: aiohttp.ClientSession, url: str) -> dict:
    page = await fetch_page(session, url)
    soup = BeautifulSoup(page, "html.parser")
    name = soup.find("h1").text.strip()
    UPC = soup.select("table tr")[0].select("td")[0].text.strip()
    price = soup.select("table tr")[2].select("td")[0].text.strip()
    tax = soup.select("table tr")[4].select("td")[0].text.strip()
    availability = soup.select("table tr")[5].select("td")[0].text.strip()

    return {
        UPC: {
            "Name": name,
            "UPC": UPC,
            "Price (excl. tax)": price,
            "Tax": tax,
            "Availability": availability,
        }
    }

async def process_books(session: aiohttp.ClientSession, book_links: list, UPC_library: dict, lock: asyncio.Lock):
    tasks = []
    for book_link in book_links:
        tasks.append(read_page(session, book_link))

    results = await asyncio.gather(*tasks)
    async with lock:
        for result in results:
            UPC_library.update(result)

async def process_category(session: aiohttp.ClientSession, category_url: str, UPC_library: dict, lock: asyncio.Lock):
    html = await fetch_page(session, category_url)
    book_links = await get_book_links(html)
    await process_books(session, book_links, UPC_library, lock)

    i = 1
    while "next" in html:
        i += 1
        next_books_link = category_url.replace("index.html", f"page-{i}.html")
        html = await fetch_page(session, next_books_link)
        book_links = await get_book_links(html)
        await process_books(session, book_links, UPC_library, lock)

async def main():
    async with aiohttp.ClientSession() as session:
        category_links = await get_category_links(session)
        UPC_library = {}
        lock = asyncio.Lock()

        tasks = [
            process_category(session, category_link, UPC_library, lock)
            for category_link in category_links
        ]

        for _ in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
            await _

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(UPC_library, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(main())
