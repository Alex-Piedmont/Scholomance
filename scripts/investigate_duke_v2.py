#!/usr/bin/env python3
"""Investigate Duke's technology listing with realistic browser settings."""

import asyncio
from playwright.async_api import async_playwright


async def main():
    print("Investigating Duke OLV with realistic browser settings...\n")

    async with async_playwright() as p:
        # Launch with more realistic settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        # Create context with realistic settings
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        page = await context.new_page()

        # Remove webdriver property
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Try the main OLV page first
        print("Loading https://olv.duke.edu/...")
        await page.goto("https://olv.duke.edu/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        title = await page.title()
        print(f"Main page title: {title}")

        if "bot" not in title.lower():
            # Try technologies page
            print("\nLoading https://olv.duke.edu/technologies/...")
            await page.goto("https://olv.duke.edu/technologies/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            title = await page.title()
            print(f"Technologies page title: {title}")

            if "bot" not in title.lower():
                # Get technology links
                tech_links = await page.query_selector_all("a[href*='/technologies/']")
                print(f"\nFound {len(tech_links)} technology links")

                # Sample technologies
                if tech_links:
                    print("\nSample technologies:")
                    seen = set()
                    for link in tech_links[:30]:
                        href = await link.get_attribute("href")
                        text = await link.inner_text()
                        text = text.strip()
                        if href and text and len(text) > 10 and href not in seen:
                            if "/technologies/" in href and href != "https://olv.duke.edu/technologies/":
                                seen.add(href)
                                print(f"  - {text[:70]}")
                                print(f"    URL: {href}")
                        if len(seen) >= 5:
                            break

                # Check for pagination
                all_links = await page.query_selector_all("a")
                for link in all_links:
                    href = await link.get_attribute("href") or ""
                    text = await link.inner_text()
                    if "page" in href.lower() or "next" in text.lower() or "load more" in text.lower():
                        print(f"\nPagination: {text.strip()} -> {href}")
            else:
                print("Still blocked on technologies page")
                # Save screenshot for debugging
                await page.screenshot(path="/tmp/duke_blocked.png")
                print("Screenshot saved to /tmp/duke_blocked.png")
        else:
            print("Blocked on main page")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
