#!/usr/bin/env python3
"""
google-ads-scraper - Google Ads Web Scraper
Google Ads Scraper - Analyze publicly visible ad results for search and competitive research

Sponsored by CoreClaw - https://www.coreclaw.com
"""

import argparse
import json
import csv
import time
import sys
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "lxml"])
    import requests
    from bs4 import BeautifulSoup


@dataclass
class ScrapedItem:
    """Data model for scraped Google Ads items."""
    id: str = ""
    title: str = ""
    description: str = ""
    url: str = ""
    date: str = ""
    author: str = ""
    rating: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    scraped_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class GoogleAdsScraper:
    """Main scraper class for Google Ads data extraction."""

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30, delay: float = 1.0):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.proxy = proxy
        self.timeout = timeout
        self.delay = delay
        self.results: List[ScrapedItem] = []

    def _get_proxies(self) -> Optional[dict]:
        if self.proxy:
            return {"http": self.proxy, "https": self.proxy}
        return None

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL."""
        try:
            time.sleep(self.delay)
            resp = self.session.get(url, proxies=self._get_proxies(), timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_results(self, html: str) -> List[ScrapedItem]:
        """Parse HTML content and extract data items."""
        soup = BeautifulSoup(html, 'lxml')
        items = []
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        # Parse logic - adapt selectors for Google Ads
        for elem in soup.select('[data-testid], .result, .item, article'):
            item = ScrapedItem(scraped_at=timestamp)
            title_elem = elem.select_one('h2, h3, .title, [data-testid="title"]')
            if title_elem:
                item.title = title_elem.get_text(strip=True)
            desc_elem = elem.select_one('.description, .summary, p')
            if desc_elem:
                item.description = desc_elem.get_text(strip=True)
            link_elem = elem.select_one('a[href]')
            if link_elem:
                item.url = link_elem.get('href', '')
            if item.title or item.url:
                item.id = str(hash(item.url or item.title))[:12]
                items.append(item)
        return items

    def scrape(self, query: str, max_results: int = 100) -> List[ScrapedItem]:
        """Scrape Google Ads data for a given query."""
        search_url = f"https://www.google ads.com/search?q={quote_plus(query)}"
        page = 1
        while len(self.results) < max_results:
            url = f"{search_url}&page={page}"
            print(f"Scraping page {page}... ({len(self.results)}/{max_results})")
            html = self.fetch_page(url)
            if not html:
                break
            items = self.parse_results(html)
            if not items:
                print("No more results found.")
                break
            self.results.extend(items)
            page += 1
            if len(self.results) >= max_results:
                break
        self.results = self.results[:max_results]
        return self.results

    def export(self, filepath: str, fmt: str = 'json') -> None:
        """Export results to JSON or CSV."""
        data = [item.to_dict() for item in self.results]
        if fmt == 'csv':
            if not data:
                print("No data to export.")
                return
            keys = data[0].keys()
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Exported {len(data)} records to {filepath}")


def main():
    parser = argparse.ArgumentParser(description='google-ads-scraper - Google Ads Web Scraper')
    parser.add_argument('--query', '-q', required=True, help='Search query or URL')
    parser.add_argument('--output', '-o', default='output.json', help='Output file path')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json', help='Output format')
    parser.add_argument('--max-results', '-m', type=int, default=100, help='Max results')
    parser.add_argument('--delay', '-d', type=float, default=1.0, help='Delay between requests')
    parser.add_argument('--proxy', '-p', default=None, help='Proxy URL')
    parser.add_argument('--timeout', '-t', type=int, default=30, help='Request timeout')
    parser.add_argument('--quiet', action='store_true', help='Suppress output')
    args = parser.parse_args()

    scraper = GoogleAdsScraper(proxy=args.proxy, timeout=args.timeout, delay=args.delay)
    scraper.scrape(args.query, args.max_results)
    scraper.export(args.output, args.format)

    if not args.quiet:
        print(f"Done! Scraped {len(scraper.results)} items from Google Ads.")


if __name__ == '__main__':
    main()
