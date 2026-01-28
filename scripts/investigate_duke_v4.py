#!/usr/bin/env python3
"""Investigate Duke's technology listing - final structure check."""

import asyncio
import re
from playwright.async_api import async_playwright


async def main():
    print("Final Duke investigation...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        # Load technologies page
        print("Loading https://olv.duke.edu/technologies/...")
        await page.goto("https://olv.duke.edu/technologies/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        # Find technology cards/listings
        # Look for the listing section
        listing = await page.query_selector(".c-listing, .technology-listing, main, #main-content")
        if listing:
            # Find all technology item containers
            items = await listing.query_selector_all("a.c-card, .c-card a, article a, .technology-card a")
            print(f"Technology cards found: {len(items)}")

            for item in items[:5]:
                href = await item.get_attribute("href") or ""
                text = await item.inner_text()
                text = ' '.join(text.split())[:80]
                if "/technologies/" in href and "/c/" not in href:
                    print(f"\n  Title: {text}")
                    print(f"  URL: {href}")

        # Let's look at the actual link pattern
        print("\n--- All unique technology URLs on page 1 ---")
        all_links = await page.query_selector_all("a")
        tech_urls = set()
        for link in all_links:
            href = await link.get_attribute("href") or ""
            # Match technology URLs but not categories
            if re.match(r'https://otc\.duke\.edu/technologies/[a-z0-9-]+/?$', href):
                tech_urls.add(href)

        print(f"Found {len(tech_urls)} unique technology URLs")
        for url in sorted(tech_urls)[:10]:
            print(f"  {url}")

        # Check how many pages
        print(f"\n--- Pagination ---")
        page_links = await page.query_selector_all("a[href*='pg=']")
        pages = set()
        for pl in page_links:
            href = await pl.get_attribute("href") or ""
            match = re.search(r'pg=(\d+)', href)
            if match:
                pages.add(int(match.group(1)))
        if pages:
            print(f"Pages found: 1 to {max(pages)}")
            print(f"Estimated total technologies: ~{len(tech_urls) * max(pages)}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
