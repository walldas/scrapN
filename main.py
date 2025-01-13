import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from tqdm import tqdm

MAIN_URL = "http://books.toscrape.com"
OUTPUT_FILE = "books_lib.json"

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
        book_links.append( f'{MAIN_URL}./catalogue/{book_url}' )
    return book_links

def read_page(page, UPC_library):
    soup = BeautifulSoup(page, "html.parser")
    name = soup.find("h1").text.strip()
    UPC = soup.select("table tr")[0].select("td")[0].text.strip()
    price = soup.select("table tr")[2].select("td")[0].text.strip()
    tax = soup.select("table tr")[4].select("td")[0].text.strip()
    availability = soup.select("table tr")[5].select("td")[0].text.strip()

    UPC_library[UPC] = {
            "Name": name,
            "UPC": UPC,
            "Price (excl. tax)": price,
            "Tax": tax,
            "Availability": availability,
        }

async def scrap_books(UPC_library, session, html):
    book_links = await get_book_links(html)
    for book_link in tqdm(book_links):
        async with aiohttp.ClientSession() as session:
            page = await fetch_page(session, book_link)
            read_page(page, UPC_library)
            
            
async def main():
    async with aiohttp.ClientSession() as session:
        category_links = await get_category_links(session)
        UPC_library = {}
        for i, category_link in enumerate(category_links):
            print(f"{i}/{len(category_links)}", category_link)

            html = await fetch_page(session, category_link)
            await scrap_books(UPC_library, session, html)

            i = 1
            while html.find("next") != -1:
                i += 1
                next_books_link = category_link.replace("index.html", f"page-{i}.html")
                print(next_books_link)
                
                html = await fetch_page(session, next_books_link)
                await scrap_books(UPC_library, session, html)



        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(UPC_library, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    asyncio.run(main())