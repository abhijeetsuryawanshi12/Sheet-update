import asyncio
import json
from pathlib import Path
import os
from playwright.async_api import async_playwright, expect
from typing import List, Dict
import time

# --- Configuration ---
COOKIES_FILE_PATH = "hiive_cookies.json"
COMPANY_TO_SEARCH = "Replit"

def normalize_cookies_for_playwright(cookies_data: list) -> list:
    """
    Normalizes cookies to fix the `sameSite` attribute for Playwright.
    """
    normalized_cookies = []
    same_site_mapping = {
        "no_restriction": "None", "unspecified": "None", "lax": "Lax", "strict": "Strict", "": "Lax"
    }
    for cookie in cookies_data:
        original_same_site = str(cookie.get("sameSite", "")).lower()
        normalized_cookies.append({
            "name": cookie["name"], "value": cookie["value"], "domain": cookie["domain"],
            "path": cookie["path"], "expires": cookie.get("expirationDate", -1),
            "httpOnly": cookie.get("httpOnly", False), "secure": cookie.get("secure", False),
            "sameSite": same_site_mapping.get(original_same_site, "Lax")
        })
    return normalized_cookies

def prepare_storage_state_from_cookies(cookie_file_path: str) -> None:
    """
    Reads the cookie file, normalizes it, and saves it in Playwright's storage_state format.
    """
    if not os.path.exists(cookie_file_path):
        raise FileNotFoundError(f"Cookie file not found: {cookie_file_path}")
    with open(cookie_file_path, 'r') as f:
        data = json.load(f)
        cookie_list = data if isinstance(data, list) else data.get("cookies", [])
        normalized = normalize_cookies_for_playwright(cookie_list)
        storage_state = {"cookies": normalized, "origins": []}
        with open(cookie_file_path, 'w') as sf:
            json.dump(storage_state, sf, indent=2)
    print(f"🍪 Cookie file '{cookie_file_path}' has been normalized for Playwright.")

async def scrape_hiive_with_playwright():
    """
    Uses the Playwright Python library directly to perform complex interactions.
    """
    try:
        prepare_storage_state_from_cookies(COOKIES_FILE_PATH)
    except Exception as e:
        print(f"❌ Error preparing cookies: {e}")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        
        # Step 1: Set up context with cookies for automatic login
        context = await browser.new_context(
            storage_state=COOKIES_FILE_PATH,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # Step 2: Navigate and Search
            print("🚀 Navigating to the Hiive dashboard...")
            await page.goto("https://app.hiive.com/dashboard", wait_until="domcontentloaded", timeout=150000)

            print(f"🔍 Searching for company: '{COMPANY_TO_SEARCH}'...")
            search_input = page.locator('input[placeholder="Search company"]')
            await expect(search_input).to_be_visible(timeout=30000)
            await search_input.click()
            await search_input.type(COMPANY_TO_SEARCH, delay=150)
            await asyncio.sleep(3)
            time.sleep(15)
            await page.keyboard.press("Enter")
            time.sleep(15)

            # print("⏳ Waiting for company page to load...")
            # company_heading = page.locator(f'h2:has-text("{COMPANY_TO_SEARCH}")')
            # await expect(company_heading).to_be_visible(timeout=60000)
            # print("✅ Company page loaded successfully.")
            
            await asyncio.sleep(5) # Allow charts and data to finish rendering

            # Step 3: Scrape the Interactive Chart
            print("📊 Starting interactive chart scraping...")

            # !!! CORRECTED SELECTORS BASED ON YOUR SCREENSHOTS !!!
            CHART_DATA_POINTS_SELECTOR = "g.visx-columns line.visx-line"
            TOOLTIP_SELECTOR = "div.g-visx-tooltip" # This is a strong guess, confirm if it fails.
            
            chart_data = []

            data_points = page.locator(CHART_DATA_POINTS_SELECTOR)
            count = await data_points.count()
            print(f"   - Found {count} data points to hover over.")

            if count == 0:
                print("   - ⚠️  Warning: Could not find any chart data points with the current selector.")
                print(f"   - Please update CHART_DATA_POINTS_SELECTOR in the script if this is wrong.")

            for i in range(count):
                point = data_points.nth(i)
                
                # Hover over the data point to trigger the tooltip
                try:
                    await point.hover(force=True, timeout=5000)
                except Exception as hover_error:
                    print(f"   - Could not hover over point {i+1}. It might be obscured. Error: {hover_error}")
                    continue
                
                # Wait for the tooltip to become visible
                tooltip = page.locator(TOOLTIP_SELECTOR)
                try:
                    await expect(tooltip).to_be_visible(timeout=5000)
                    # Scrape the text from the tooltip
                    tooltip_text = await tooltip.inner_text()
                    
                    # Process the text and add it to our data list
                    cleaned_text = tooltip_text.replace("\n", " | ")
                    print(f"   - Scraped Tooltip {i+1}: {cleaned_text}")
                    chart_data.append(cleaned_text)
                except Exception as tooltip_error:
                    print(f"   - Tooltip did not appear for point {i+1} or selector is wrong. Error: {tooltip_error}")
                    continue
                
                # A small delay to ensure the page keeps up
                await asyncio.sleep(0.1)

            print("\n✅ Chart scraping successful!")
            print("Collected Data:")
            print(json.dumps(chart_data, indent=2))


        except Exception as e:
            print(f"❌ An error occurred during the scraping process: {e}")
            await page.screenshot(path="playwright_error.png")
            print("   - A screenshot 'playwright_error.png' has been saved for debugging.")

        finally:
            print("\nClosing the browser in 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_hiive_with_playwright())