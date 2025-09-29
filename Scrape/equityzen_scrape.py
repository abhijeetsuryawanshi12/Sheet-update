import asyncio
import json
import random
import time
import sys
import os

from playwright.async_api import async_playwright, expect

# --- Add parent directory to path to import 'app' modules ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.google_sheets import GoogleSheetsClient

# --- Configuration ---
COOKIES_FILE_PATH = "Scrape/equityzen_cookies.json"
COMPANY_NAME = "Replit" # This is used for the Google Sheet row
COMPANY_URL_SLUG = "replit" # This is the part that goes in the URL

def normalize_cookies(cookies_data):
    """
    Converts cookies from a browser-exported JSON file into the format
    required by Playwright's context.add_cookies() method.
    """
    normalized_cookies = []
    for cookie in cookies_data:
        same_site_mapping = {
            "no_restriction": "None", "unspecified": "None", "lax": "Lax", "strict": "Strict"
        }
        new_cookie = {
            "name": cookie["name"], "value": cookie["value"], "domain": cookie["domain"],
            "path": cookie["path"], "expires": cookie.get("expirationDate", -1),
            "httpOnly": cookie.get("httpOnly", False), "secure": cookie.get("secure", False),
            "sameSite": same_site_mapping.get(str(cookie.get("sameSite", "")).lower(), "Lax")
        }
        normalized_cookies.append(new_cookie)
    return normalized_cookies

async def main():
    """
    Main function to run the EquityZen scraping process.
    """
    target_url = f"https://equityzen.com/company/{COMPANY_URL_SLUG}/"

    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies_from_file = json.load(f)
        cookies = normalize_cookies(cookies_from_file)
        print(f"✅ Successfully loaded and normalized {len(cookies)} cookies from '{COOKIES_FILE_PATH}'.")

    except FileNotFoundError:
        print(f"❌ Error: Cookie file not found at '{COOKIES_FILE_PATH}'.")
        print("   Please log into equityzen.com, export your cookies, and save them as 'equityzen_cookies.json' in the 'Scrape' folder.")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: The cookie file at '{COOKIES_FILE_PATH}' is not a valid JSON file.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            # 1. Navigate directly to the company page
            print(f"🚀 Navigating to EquityZen page: {target_url}...")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            print("   - Page loaded.")
            await asyncio.sleep(random.uniform(3, 5))

            # 2. Scrape the "Market Activity" data
            print("💰 Scraping the 'Market Activity' card...")
            
            # This selector is robust and looks for a div whose class CONTAINS "MarketActivityCard--items"
            items_container = page.locator('div[class*="MarketActivityCard--items"]')
            await expect(items_container).to_be_visible(timeout=30000)

            # Find all the individual data items within the container
            all_items = items_container.locator('div[class*="MarketActivityCard--item"]')
            count = await all_items.count()
            print(f"   - Found {count} data points in the card.")

            data = {}
            for i in range(count):
                item = all_items.nth(i)
                # Use robust selectors for label and value
                label_locator = item.locator('div[class*="--item-label"]')
                value_locator = item.locator('div[class*="--item-value"]')
                
                # Check if both label and value exist before trying to get text
                if await label_locator.count() > 0 and await value_locator.count() > 0:
                    label = await label_locator.inner_text()
                    value = await value_locator.inner_text()
                    if label and value and value != '--': # Ignore empty or placeholder values
                        data[label.strip()] = value.strip()

            if not data:
                print("❌ Warning: Could not scrape any data. The page structure might have changed.")
                return

            print("✅ Scraping successful!")
            print(json.dumps(data, indent=2))
            
            # 3. Update Google Sheet
            if data:
                print("\n🔄 Attempting to update Google Sheet...")
                gs_client = GoogleSheetsClient()
                success = gs_client.update_or_add_company_data(
                    company_name=COMPANY_NAME,
                    data=data
                )
                if success:
                    print("✅ Google Sheet update process finished successfully.")
                else:
                    print("❌ Google Sheet update process failed. Check logs for errors.")

        except Exception as e:
            print(f"❌ An error occurred during the scraping process: {e}")
            await page.screenshot(path="equityzen_scraping_error.png")
            print("   - A screenshot 'equityzen_scraping_error.png' has been saved for debugging.")

        finally:
            print("\nClosing the browser in 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
