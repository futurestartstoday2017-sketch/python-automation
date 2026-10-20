"""quotes.toscrape.com/js から名言と著者名を Playwright で取得し、Markdown とスクリーンショットに保存する。"""

import logging
import random
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

BASE_URL = "https://quotes.toscrape.com/"
START_URL = urljoin(BASE_URL, "js/")
USER_AGENT = "python-automation-quote-scraper/1.0"
TIMEOUT_MS = 15_000
WAIT_RANGE_SECONDS = (1.0, 3.0)
OUTPUT_DIR = Path(__file__).parent
LOG_FILE = OUTPUT_DIR / "scrape_quotes.log"

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


def load_robots() -> RobotFileParser:
    """robots.txt を読み込む。存在しない場合 (4xx) はすべて許可とみなす。"""
    robots_url = urljoin(BASE_URL, "robots.txt")
    parser = RobotFileParser(robots_url)
    try:
        response = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_MS / 1000)
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


def open_page(page: Page, url: str) -> None:
    """ページを開き、名言が描画されるまで待つ。接続エラーなどの場合はログを出力して終了する。"""
    try:
        response = page.goto(url, timeout=TIMEOUT_MS)
        if response is None or not response.ok:
            status = response.status if response else "不明"
            logger.error("ページの取得に失敗しました: %s (HTTP %s)", url, status)
            sys.exit(1)
        page.wait_for_selector("div.quote", timeout=TIMEOUT_MS)
    except PlaywrightError as e:
        logger.error("接続エラーが発生しました: %s (%s)", url, e.message.splitlines()[0])
        sys.exit(1)


def parse_quotes(page: Page) -> list[dict[str, str]]:
    quotes = []
    for quote in page.locator("div.quote").all():
        quotes.append({
            "text": quote.locator("span.text").inner_text().strip(),
            "author": quote.locator("small.author").inner_text().strip(),
        })
    return quotes


def scrape(page: Page, robots: RobotFileParser, screenshot_path: Path) -> list[dict[str, str]]:
    quotes: list[dict[str, str]] = []
    url: str | None = START_URL
    page_no = 0
    while url:
        if not robots.can_fetch(USER_AGENT, url):
            logger.warning("robots.txt で禁止されているためスキップします: %s", url)
            break
        if page_no > 0:
            time.sleep(random.uniform(*WAIT_RANGE_SECONDS))
        page_no += 1
        logger.info("ページ %d を取得中: %s", page_no, url)
        open_page(page, url)
        if page_no == 1:
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info("スクリーンショットを %s に保存しました", screenshot_path.name)
        quotes.extend(parse_quotes(page))
        next_link = page.locator("li.next a")
        url = urljoin(url, next_link.get_attribute("href")) if next_link.count() else None
    return quotes


def escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def save_markdown(quotes: list[dict[str, str]], path: Path, today: date) -> None:
    lines = [
        f"# 名言一覧 ({today:%Y-%m-%d})",
        "",
        f"- 取得元: {START_URL}",
        f"- 取得件数: {len(quotes)} 件",
        "",
        "| No. | 名言 | 著者 |",
        "| ---: | --- | --- |",
    ]
    for i, quote in enumerate(quotes, start=1):
        lines.append(f"| {i} | {escape_md(quote['text'])} | {escape_md(quote['author'])} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    setup_logging()
    today = date.today()
    md_path = OUTPUT_DIR / f"quotes_{today:%Y%m%d}.md"
    png_path = OUTPUT_DIR / f"quotes_{today:%Y%m%d}.png"

    robots = load_robots()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            quotes = scrape(page, robots, png_path)
        finally:
            browser.close()

    save_markdown(quotes, md_path, today)
    logger.info("%d 件の名言を %s に保存しました", len(quotes), md_path.name)


if __name__ == "__main__":
    main()
