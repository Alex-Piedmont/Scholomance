#!/usr/bin/env python3
"""Debug Duke scraper issue."""

import asyncio
import re
from playwright.async_api import async_playwright


async def main():
    print("Debugging Duke scraper...\n")

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

        # Load page 1
        url = "https://otc.duke.edu/technologies/"
        print(f"Loading {url}...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        title = await page.title()
        print(f"Page title: {title}")

        # Get all links
        all_links = await page.query_selector_all("a")
        print(f"Total links on page: {len(all_links)}")

        # Find technology URLs
        tech_urls = []
        for link in all_links:
            href = await link.get_attribute("href") or ""
            # Match technology URLs
            if re.match(r'https://otc\.duke\.edu/technologies/[a-z0-9-]+/?$', href):
                text = await link.inner_text()
                tech_urls.append((href, text.strip()))

        print(f"\nTechnology URLs found: {len(tech_urls)}")
        for href, text in tech_urls[:5]:
            print(f"  {text[:50]}: {href}")

        # Try with different patterns
        print("\n--- Trying broader patterns ---")
        for link in all_links:
            href = await link.get_attribute("href") or ""
            if "/technologies/" in href and "/c/" not in href:
                text = await link.inner_text()
                text = text.strip()
                if text and len(text) > 10:
                    # Check if it's a real tech URL
                    if href.count('/') >= 4 and not href.endswith('/technologies/'):
                        print(f"  Found: {text[:50]} -> {href}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
