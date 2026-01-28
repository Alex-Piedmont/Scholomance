#!/usr/bin/env python3
"""Extract Flintbox API credentials from university sites using Playwright."""

import asyncio
import re
from playwright.async_api import async_playwright

FLINTBOX_SITES = [
    ("ucf", "University of Central Florida", "https://ucf.flintbox.com"),
    ("colorado", "University of Colorado", "https://colorado.flintbox.com"),
    ("usc", "University of Southern California", "https://usc.flintbox.com"),
    ("usu", "Utah State University", "https://usu.flintbox.com"),
    ("ttu", "Texas Tech University", "https://ttu.flintbox.com"),
    ("uconn", "University of Connecticut", "https://uconn.flintbox.com"),
    ("louisville", "University of Louisville", "https://louisville.flintbox.com"),
    ("iowa", "University of Iowa", "https://uiowa.flintbox.com"),
]


async def extract_credentials(page, code: str, name: str, url: str) -> dict:
    """Extract Flintbox credentials from a university site."""
    result = {
        "code": code,
        "name": name,
        "url": url,
        "organization_id": None,
        "access_key": None,
        "error": None,
    }

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait for the app to load
        await asyncio.sleep(2)

        # Try to get credentials from page content or network requests
        # Flintbox typically stores these in window.__ENV__ or similar

        # Method 1: Check for inline scripts with credentials
        content = await page.content()

        # Look for organizationId pattern
        org_match = re.search(r'organizationId["\s:]+["\']?(\d+)["\']?', content)
        if org_match:
            result["organization_id"] = org_match.group(1)

        # Look for accessKey/organizationAccessKey pattern
        key_match = re.search(r'(?:access[Kk]ey|organizationAccessKey)["\s:]+["\']?([a-f0-9-]{36})["\']?', content)
        if key_match:
            result["access_key"] = key_match.group(1)

        # Method 2: Try to extract from React/Vue state or window object
        if not result["organization_id"] or not result["access_key"]:
            try:
                # Check window.__INITIAL_STATE__ or similar
                js_result = await page.evaluate("""() => {
                    // Check various places where credentials might be stored
                    const checks = [
                        window.__ENV__,
                        window.__INITIAL_STATE__,
                        window.__CONFIG__,
                        window.config,
                        window.ENV,
                    ];

                    for (const obj of checks) {
                        if (obj && (obj.organizationId || obj.accessKey)) {
                            return obj;
                        }
                    }

                    // Try to find in any script tags
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const text = script.textContent || '';
                        if (text.includes('organizationId') || text.includes('accessKey')) {
                            return { scriptContent: text.substring(0, 2000) };
                        }
                    }

                    return null;
                }""")

                if js_result:
                    if "organizationId" in js_result:
                        result["organization_id"] = str(js_result["organizationId"])
                    if "accessKey" in js_result:
                        result["access_key"] = js_result["accessKey"]
                    if "organizationAccessKey" in js_result:
                        result["access_key"] = js_result["organizationAccessKey"]

            except Exception as e:
                pass

        # Method 3: Intercept API calls to get credentials
        if not result["organization_id"] or not result["access_key"]:
            # Navigate to technologies page which will trigger API call
            try:
                await page.goto(f"{url}/technologies", wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                content = await page.content()

                org_match = re.search(r'organizationId["\s:=]+["\']?(\d+)["\']?', content)
                if org_match:
                    result["organization_id"] = org_match.group(1)

                key_match = re.search(r'(?:access[Kk]ey|organizationAccessKey)["\s:=]+["\']?([a-f0-9-]{36})["\']?', content)
                if key_match:
                    result["access_key"] = key_match.group(1)
            except:
                pass

    except Exception as e:
        result["error"] = str(e)

    return result


async def main():
    print("Extracting Flintbox credentials from university sites...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        results = []
        for code, name, url in FLINTBOX_SITES:
            print(f"Checking {name}...")
            result = await extract_credentials(page, code, name, url)
            results.append(result)

            if result["organization_id"] and result["access_key"]:
                print(f"  ✓ Found credentials")
            elif result["error"]:
                print(f"  ✗ Error: {result['error']}")
            else:
                print(f"  ? Partial: org_id={result['organization_id']}, key={result['access_key']}")

        await browser.close()

    # Print summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    found = []
    not_found = []

    for r in results:
        if r["organization_id"] and r["access_key"]:
            found.append(r)
            print(f"\n{r['name']} ({r['code']}):")
            print(f"  BASE_URL = \"{r['url']}\"")
            print(f"  ORGANIZATION_ID = \"{r['organization_id']}\"")
            print(f"  ACCESS_KEY = \"{r['access_key']}\"")
        else:
            not_found.append(r)

    if not_found:
        print("\n" + "-" * 70)
        print("COULD NOT EXTRACT:")
        for r in not_found:
            print(f"  - {r['name']}: org_id={r['organization_id']}, key={r['access_key']}")
            if r["error"]:
                print(f"    Error: {r['error']}")

    print(f"\n\nSummary: {len(found)}/{len(results)} universities extracted successfully")


if __name__ == "__main__":
    asyncio.run(main())
