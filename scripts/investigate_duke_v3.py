#!/usr/bin/env python3
"""Investigate Duke's technology listing structure in detail."""

import asyncio
import re
from playwright.async_api import async_playwright


async def main():
    print("Investigating Duke OLV technology structure...\n")

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
        print("Loading technologies page...")
        await page.goto("https://olv.duke.edu/technologies/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        # Find all links and categorize them
        all_links = await page.query_selector_all("a[href*='/technologies/']")

        categories = []
        technologies = []

        for link in all_links:
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).strip()

            if "/technologies/c/" in href:
                # Category link
                categories.append((text, href))
            elif "/technologies/" in href and href != "/technologies/" and href != "https://olv.duke.edu/technologies/":
                # Potential technology link
                if not any(x in href for x in ["/c/", "?pg=", "?s="]):
                    technologies.append((text, href))

        print(f"\nCategories found: {len(categories)}")
        print(f"Direct technology links found: {len(technologies)}")

        # Show sample technologies
        if technologies:
            print("\nSample technology links:")
            seen = set()
            for text, href in technologies[:10]:
                if href not in seen and text:
                    seen.add(href)
                    print(f"  - {text[:60]}")
                    print(f"    {href}")

        # Check pagination
        print("\n--- Checking pagination ---")
        next_link = await page.query_selector("a[href*='pg=2'], a:has-text('Next')")
        if next_link:
            href = await next_link.get_attribute("href")
            print(f"Next page link: {href}")

        # Count total pages by looking at pagination
        pager_links = await page.query_selector_all("a[href*='pg=']")
        max_page = 1
        for plink in pager_links:
            href = await plink.get_attribute("href") or ""
            match = re.search(r'pg=(\d+)', href)
            if match:
                max_page = max(max_page, int(match.group(1)))
        print(f"Max page found: {max_page}")

        # Try to get count from page
        content = await page.content()
        count_match = re.search(r'(\d+)\s*(?:technologies|results|items)', content, re.I)
        if count_match:
            print(f"Count found in page: {count_match.group(0)}")

        # Look at the HTML structure for technology cards
        print("\n--- Examining page structure ---")

        # Find the main listing container
        articles = await page.query_selector_all("article, .technology-item, .listing-item, [class*='tech']")
        print(f"Article/item elements: {len(articles)}")

        # Get a sample article structure
        if articles:
            first_article = articles[0]
            article_html = await first_article.inner_html()
            print(f"\nFirst article HTML preview:\n{article_html[:500]}...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
