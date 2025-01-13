import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from tqdm import tqdm

# Duomenų rinkimo funkcija
async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        return await response.text()


# Duomenų ištraukimas pagal schemą
async def parse_book(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    name = soup.find("h1").text.strip()
    table = soup.find("table", {"class": "table table-striped"})
    data = {row.find("th").text: row.find("td").text.strip() for row in table.find_all("tr")}
    
    availability = soup.find("p", {"class": "instock availability"}).text.strip()
    return {
        "Name": name,
        "UPC": data.get("UPC", ""),
        "Price (excl. tax)": data.get("Price (excl. tax)", ""),
        "Tax": data.get("Tax", ""),
        "Availability": availability,
    }


# Puslapio apdorojimas
async def process_page(session: aiohttp.ClientSession, url: str) -> list:
    html = await fetch_page(session, url)
    soup = BeautifulSoup(html, "html.parser")
    book_links = [a["href"] for a in soup.select("h3 a")]
    book_urls = [f"http://books.toscrape.com/catalogue/{link}" for link in (book_links)]

    tasks = [fetch_page(session, book_url) for book_url in book_urls]
    book_pages = await asyncio.gather(*tasks)

    parse_tasks = [parse_book(page) for page in book_pages]
    return await asyncio.gather(*parse_tasks)


# Pagrindinė funkcija
async def main():
    base_url = "http://books.toscrape.com/catalogue/page-{}.html"
    results = []
    seen = set()

    async with aiohttp.ClientSession() as session:
        for page in tqdm(range(1, 51)):  # Tikriname pirmus 2 puslapius kaip pavyzdį
            url = base_url.format(page)
            books = await process_page(session, url)

            # Validacija ir duomenų deduplicavimas
            for book in books:
                if book["UPC"] not in seen:
                    seen.add(book["UPC"])
                    results.append(book)

    # Duomenų išsaugojimas JSON faile
    with open("books_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    asyncio.run(main())
