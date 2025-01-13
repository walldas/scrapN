import requests
from bs4 import BeautifulSoup
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

MAIN_URL = "http://books.toscrape.com"
OUTPUT_FILE = "books_lib.json"

def fetch_page(url: str) -> str:
    response = requests.get(url)
    return response.text
    
def get_category_links() -> list:
    html = fetch_page(MAIN_URL)
    soup = BeautifulSoup(html, "html.parser")
    category_links = soup.select("div.side_categories ul > li > ul > li > a")
    return [f'{MAIN_URL}/{a["href"]}' for a in category_links]

def get_book_links(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    book_links = []
    for a in soup.select("h3 a"):
        book_url = a["href"].replace("../../../", "")
        book_links.append(f'{MAIN_URL}/catalogue/{book_url}')
    return book_links

def read_page(page: str) -> dict:
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

def process_single_book(book_link: str, UPC_library: dict, lock: Lock) -> None:
    page = fetch_page(book_link)
    result = read_page(page)
    with lock:
        UPC_library.update(result)

def process_books(book_links: list, UPC_library: dict, lock: Lock) -> None:
    with ThreadPoolExecutor(max_workers=len(book_links)) as book_executor:
        futures = []
        for link in book_links:
            book_executor.submit(process_single_book, link, UPC_library, lock)
        
        for future in (futures):
            future.result()

def process_category(category_url: str, UPC_library: dict, lock: Lock) -> None:
    html = fetch_page(category_url)
    book_links = get_book_links(html)
    process_books(book_links, UPC_library, lock)
    
    i = 1
    while html.find("next") != -1:
        i += 1
        next_books_link = category_url.replace("index.html", f"page-{i}.html")
        html = fetch_page(next_books_link)
        book_links = get_book_links(html)
        process_books(book_links, UPC_library, lock)

def main() -> None:
    category_links = get_category_links()
    UPC_library = {}
    lock = Lock()
    
    with ThreadPoolExecutor(max_workers=len(category_links)) as executor:
        futures = []
        # for category_link in category_links:
        #     executor.submit(process_category, category_link, UPC_library, lock)
        for category_link in tqdm(category_links, desc="Processing Categories"):
            futures.append(executor.submit(process_category, category_link, UPC_library, lock))

        # for i, future in tqdm(enumerate(futures)):
        #     # print(f"{i}/{len(category_links)}")
        #     future.result()
        for future in tqdm(futures, desc="Finalizing Tasks", total=len(futures)):
            future.result()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(UPC_library, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()