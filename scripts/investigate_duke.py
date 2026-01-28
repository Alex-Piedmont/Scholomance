#!/usr/bin/env python3
"""Investigate Duke's technology listing structure using Playwright."""

import asyncio
from playwright.async_api import async_playwright


async def main():
    print("Investigating Duke OLV website structure...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Try the technologies page
        print("Loading https://olv.duke.edu/technologies/...")
        await page.goto("https://olv.duke.edu/technologies/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

        # Get page title
        title = await page.title()
        print(f"Page title: {title}")

        # Check for technology listings
        content = await page.content()

        # Look for technology links
        tech_links = await page.query_selector_all("a[href*='/technologies/']")
        print(f"\nFound {len(tech_links)} technology links")

        # Sample some links
        if tech_links:
            print("\nSample technology links:")
            seen = set()
            for link in tech_links[:20]:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                text = text.strip()[:60] if text else ""
                if href and href not in seen and "/technologies/" in href and text:
                    seen.add(href)
                    print(f"  - {text}: {href}")
                if len(seen) >= 5:
                    break

        # Look for pagination
        pagination = await page.query_selector_all("a[href*='page='], .pagination a, nav.pagination a, .pager a")
        print(f"\nPagination elements found: {len(pagination)}")

        # Check for any data attributes or IDs
        print("\nLooking for listing container...")
        containers = await page.query_selector_all("[class*='technolog'], [class*='listing'], [class*='grid'], [class*='card']")
        for c in containers[:5]:
            class_name = await c.get_attribute("class")
            print(f"  Container class: {class_name}")

        # Check if there's infinite scroll or load more
        load_more = await page.query_selector("button[class*='load'], a[class*='load'], [class*='more']")
        if load_more:
            text = await load_more.inner_text()
            print(f"\nLoad more button found: {text}")

        # Look for category/filter links
        print("\nLooking for category structure...")
        category_links = await page.query_selector_all("a[href*='category'], a[href*='type'], .filter a")
        for cat in category_links[:5]:
            href = await cat.get_attribute("href")
            text = await cat.inner_text()
            print(f"  Category: {text.strip()} -> {href}")

        # Try to find total count
        count_elements = await page.query_selector_all("[class*='count'], [class*='total'], [class*='result']")
        for el in count_elements[:3]:
            text = await el.inner_text()
            if text.strip():
                print(f"\nCount element: {text.strip()}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
