#!/usr/bin/env python3
"""Extract Flintbox API credentials by intercepting network requests."""

import asyncio
import json
import re
from urllib.parse import parse_qs, urlparse
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


async def extract_credentials(browser, code: str, name: str, base_url: str) -> dict:
    """Extract Flintbox credentials by intercepting API calls."""
    result = {
        "code": code,
        "name": name,
        "url": base_url,
        "organization_id": None,
        "access_key": None,
        "error": None,
    }

    page = await browser.new_page()

    captured_params = {}

    def handle_request(request):
        url = request.url
        # Look for API calls to Flintbox
        if "/api/" in url and "technologies" in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if "organizationId" in params:
                captured_params["organization_id"] = params["organizationId"][0]
            if "organizationAccessKey" in params:
                captured_params["access_key"] = params["organizationAccessKey"][0]

    page.on("request", handle_request)

    try:
        # Go to technologies page to trigger API call
        await page.goto(f"{base_url}/technologies", wait_until="networkidle", timeout=45000)
        await asyncio.sleep(3)

        if captured_params:
            result["organization_id"] = captured_params.get("organization_id")
            result["access_key"] = captured_params.get("access_key")
        else:
            # Try scrolling or clicking to trigger more API calls
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            if captured_params:
                result["organization_id"] = captured_params.get("organization_id")
                result["access_key"] = captured_params.get("access_key")

    except Exception as e:
        result["error"] = str(e)
    finally:
        await page.close()

    return result


async def main():
    print("Extracting Flintbox credentials by intercepting API calls...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        results = []
        for code, name, url in FLINTBOX_SITES:
            print(f"Checking {name}...")
            result = await extract_credentials(browser, code, name, url)
            results.append(result)

            if result["organization_id"] and result["access_key"]:
                print(f"  ✓ Found credentials")
            elif result["error"]:
                print(f"  ✗ Error: {result['error'][:50]}...")
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
                print(f"    Error: {r['error'][:80]}")

    print(f"\n\nSummary: {len(found)}/{len(results)} universities extracted successfully")

    # Output as Python dict for easy copy-paste
    if found:
        print("\n" + "=" * 70)
        print("PYTHON CONFIG:")
        print("=" * 70)
        print("\nFLINTBOX_UNIVERSITIES = {")
        for r in found:
            print(f'    "{r["code"]}": {{')
            print(f'        "name": "{r["name"]}",')
            print(f'        "base_url": "{r["url"]}",')
            print(f'        "organization_id": "{r["organization_id"]}",')
            print(f'        "access_key": "{r["access_key"]}",')
            print(f'    }},')
        print("}")


if __name__ == "__main__":
    asyncio.run(main())
