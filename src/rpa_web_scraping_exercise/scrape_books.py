from decimal import Decimal
from typing import TypedDict
from urllib.parse import urljoin

from playwright.sync_api import Page

URL: str = "https://books.toscrape.com/"


class BookData(TypedDict):
    url: str
    name: str
    rating: int
    price: Decimal
    in_stock: bool


def scrape_books(page: Page, *, category: str | None, max_books: int) -> list[BookData]:
    """Scrape book data from https://books.toscrape.com/.

    After navigating to the site homepage, scrapes book data following this
    contract:

    - `category` is `None`: scrape all books, following the pagination from
      the homepage without navigating into any category.
    - `category` matches a sidebar category (case-insensitive): scrape only
      that category's books, following its pagination.
    - `category` does not match any sidebar category (or is empty /
      whitespace-only): return an empty list.

    Stops as soon as `max_books` books have been collected and never request
    pages beyond the limit. If `max_books` is less than or equal to zero, an
    empty list is returned.

    Args:
        page: A Playwright page, already created and navigable.
        category: The category to scrape, or `None` to scrape all books.
        max_books: Maximum number of books to scrape.

    Returns:
        A list of the scraped books.
    """
    if max_books <= 0:
        return []

    rating_map = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5,
    }

    results: list[BookData] = []

    page.goto(URL)

    category_links = page.locator(".side_categories ul ul a")

    if category is not None:
        found_category = False
        if not category.strip():
            return []

        for i in range(category_links.count()):
            category_link = category_links.nth(i)
            category_name = category_link.inner_text().strip()

            if category_name.lower() == category.strip().lower():
                found_category = True
                category_href = category_link.get_attribute("href")
                assert category_href is not None
                category_url = urljoin(page.url, category_href)
                page.goto(category_url)
                break
        if not found_category:
            return []

    while True:
        books = page.locator("article.product_pod")
        remaining = max_books - len(results)

        for i in range(min(books.count(), remaining)):
            book = books.nth(i)

            link = book.locator("h3 a")
            name = link.get_attribute("title")
            assert name is not None

            href = link.get_attribute("href")
            assert href is not None
            url = urljoin(page.url, href)

            price_text = book.locator(".price_color").inner_text()
            price = Decimal(price_text.removeprefix("£"))

            stock_text = book.locator(".availability").inner_text()
            in_stock = stock_text.strip().lower() == "in stock"

            rating_element = book.locator(".star-rating")
            classes = rating_element.get_attribute("class")
            assert classes is not None
            rating_class = classes.split()[1]
            rating = rating_map[rating_class]

            book_data: BookData = {
                "url": url,
                "name": name,
                "rating": rating,
                "price": price,
                "in_stock": in_stock,
            }

            results.append(book_data)

        if len(results) >= max_books:
            return results

        next_link = page.locator("li.next a")

        if next_link.count() == 0:
            return results

        next_href = next_link.get_attribute("href")
        assert next_href is not None
        next_page = urljoin(page.url, next_href)

        page.goto(next_page)
