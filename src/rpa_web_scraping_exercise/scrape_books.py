from decimal import Decimal
from typing import TypedDict
from urllib.parse import urljoin

from playwright.sync_api import Locator, Page

URL: str = "https://books.toscrape.com/"

RATING_MAP: dict[str, int] = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


class BookData(TypedDict):
    url: str
    name: str
    rating: int
    price: Decimal
    in_stock: bool


def find_category_url(page: Page, category: str) -> str | None:
    """Return the URL for a sidebar category, if it exists."""
    category_links = page.locator(".side_categories ul ul a")
    category_name = category.strip().lower()

    for i in range(category_links.count()):
        link = category_links.nth(i)

        if link.inner_text().strip().lower() == category_name:
            href = link.get_attribute("href")
            assert href is not None
            return urljoin(page.url, href)

    return None


def parse_rating(rating_class: str) -> int:
    """Convert a book's rating class into its numeric value."""
    rating_name = rating_class.split()[1]
    return RATING_MAP[rating_name]


def extract_book_data(book: Locator, page: Page) -> BookData:
    """Extract the required data from one book card."""
    link = book.locator("h3 a")

    name = link.get_attribute("title")
    assert name is not None

    href = link.get_attribute("href")
    assert href is not None

    price_text = book.locator(".price_color").inner_text()
    stock_text = book.locator(".availability").inner_text()

    rating_class = book.locator(".star-rating").get_attribute("class")
    assert rating_class is not None

    return {
        "url": urljoin(page.url, href),
        "name": name,
        "rating": parse_rating(rating_class),
        "price": Decimal(price_text.removeprefix("£")),
        "in_stock": stock_text.strip().lower() == "in stock",
    }


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

    Stops as soon as `max_books` books have been collected and never requests
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

    page.goto(URL)

    if category is not None:
        if not category.strip():
            return []

        category_url = find_category_url(page, category)
        if category_url is None:
            return []

        page.goto(category_url)

    results: list[BookData] = []

    while True:
        books = page.locator("article.product_pod")
        remaining = max_books - len(results)

        for i in range(min(books.count(), remaining)):
            results.append(extract_book_data(books.nth(i), page))

        if len(results) >= max_books:
            return results

        next_link = page.locator("li.next a")
        if next_link.count() == 0:
            return results

        next_href = next_link.get_attribute("href")
        assert next_href is not None

        page.goto(urljoin(page.url, next_href))
