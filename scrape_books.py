"""books.toscrape.com から書籍のタイトル・価格・在庫状況を取得し、Markdown に保存する。"""

import logging
import random
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
USER_AGENT = "python-automation-book-scraper/1.0"
TIMEOUT_SECONDS = 10
WAIT_RANGE_SECONDS = (1.0, 3.0)
OUTPUT_DIR = Path(__file__).parent
LOG_FILE = OUTPUT_DIR / "scrape_books.log"

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def fetch(session: requests.Session, url: str) -> requests.Response:
    """URL を取得する。接続エラーなどの場合はログを出力して終了する。"""
    try:
        response = session.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        logger.error("接続エラーが発生しました: %s (%s)", url, e)
        sys.exit(1)
    except requests.exceptions.Timeout:
        logger.error("タイムアウトしました: %s", url)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logger.error("リクエストに失敗しました: %s (%s)", url, e)
        sys.exit(1)
    response.encoding = "utf-8"
    return response


def load_robots(session: requests.Session) -> RobotFileParser:
    """robots.txt を読み込む。存在しない場合 (4xx) はすべて許可とみなす。"""
    robots_url = urljoin(BASE_URL, "robots.txt")
    parser = RobotFileParser(robots_url)
    try:
        response = session.get(robots_url, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as e:
        logger.error("robots.txt の取得中に接続エラーが発生しました: %s", e)
        sys.exit(1)

    if response.status_code == 200:
        parser.parse(response.text.splitlines())
        logger.info("robots.txt を読み込みました")
    elif 400 <= response.status_code < 500:
        parser.allow_all = True
        logger.info("robots.txt がありません (HTTP %d)。すべてのパスを許可とみなします", response.status_code)
    else:
        parser.disallow_all = True
        logger.warning("robots.txt を取得できません (HTTP %d)。安全のためすべてのパスを禁止とみなします", response.status_code)
    return parser


def parse_books(html: str) -> tuple[list[dict[str, str]], str | None]:
    """一覧ページから書籍情報と次ページの相対 URL を取り出す。"""
    soup = BeautifulSoup(html, "html.parser")
    books = []
    for article in soup.select("article.product_pod"):
        books.append({
            "title": article.h3.a["title"],
            "price": article.select_one("p.price_color").get_text(strip=True),
            "availability": article.select_one("p.availability").get_text(strip=True),
        })
    next_link = soup.select_one("li.next a")
    return books, next_link["href"] if next_link else None


def scrape(session: requests.Session, robots: RobotFileParser) -> list[dict[str, str]]:
    books: list[dict[str, str]] = []
    url: str | None = BASE_URL
    page = 0
    while url:
        if not robots.can_fetch(USER_AGENT, url):
            logger.warning("robots.txt で禁止されているためスキップします: %s", url)
            break
        if page > 0:
            time.sleep(random.uniform(*WAIT_RANGE_SECONDS))
        page += 1
        logger.info("ページ %d を取得中: %s", page, url)
        page_books, next_href = parse_books(fetch(session, url).text)
        books.extend(page_books)
        url = urljoin(url, next_href) if next_href else None
    return books


def escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def save_markdown(books: list[dict[str, str]], today: date) -> Path:
    path = OUTPUT_DIR / f"books_{today:%Y%m%d}.md"
    in_stock = sum(1 for b in books if b["availability"] == "In stock")
    lines = [
        f"# 書籍一覧 ({today:%Y-%m-%d})",
        "",
        f"- 取得元: {BASE_URL}",
        f"- 取得件数: {len(books)} 件（在庫あり: {in_stock} 件）",
        "",
        "| No. | タイトル | 価格 | 在庫状況 |",
        "| ---: | --- | ---: | --- |",
    ]
    for i, book in enumerate(books, start=1):
        lines.append(
            f"| {i} | {escape_md(book['title'])} | {book['price']} | {book['availability']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    setup_logging()
    with requests.Session() as session:
        session.headers["User-Agent"] = USER_AGENT
        robots = load_robots(session)
        books = scrape(session, robots)
    path = save_markdown(books, date.today())
    logger.info("%d 件の書籍を %s に保存しました", len(books), path.name)


if __name__ == "__main__":
    main()
