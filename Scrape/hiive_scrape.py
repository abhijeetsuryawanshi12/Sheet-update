# Scrape/hiive_scrape.py
import asyncio
import json
import random
import time
import sys
import os

from playwright.async_api import async_playwright, expect

# --- Add parent directory to path to import 'app' modules ---
# This allows the script to be run from the project root or its own directory.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.google_sheets import GoogleSheetsClient

# --- Configuration ---
COOKIES_FILE_PATH = "Scrape/hiive_cookies.json"
COMPANY_TO_SEARCH = "Replit"

def normalize_cookies(cookies_data):
    """
    Converts cookies from a browser-exported JSON file into the format
    required by Playwright's context.add_cookies() method.
    """
    normalized_cookies = []
    for cookie in cookies_data:
        same_site_mapping = {
            "no_restriction": "None",
            "unspecified": "None",
            "lax": "Lax",
            "strict": "Strict"
        }
        
        new_cookie = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"],
            "path": cookie["path"],
            "expires": cookie.get("expirationDate", -1),
            "httpOnly": cookie.get("httpOnly", False),
            "secure": cookie.get("secure", False),
            "sameSite": same_site_mapping.get(str(cookie.get("sameSite", "")).lower(), "Lax")
        }
        normalized_cookies.append(new_cookie)
    return normalized_cookies

async def main():
    """
    Main function to run the scraping process.
    """
    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies_from_file = json.load(f)
        cookies = normalize_cookies(cookies_from_file)
        print(f"✅ Successfully loaded and normalized {len(cookies)} cookies.")

    except FileNotFoundError:
        print(f"❌ Error: Cookie file not found at '{COOKIES_FILE_PATH}'.")
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
            # 1. Navigate to the dashboard
            print("🚀 Navigating to the Hiive dashboard...")
            await page.goto("https://app.hiive.com/dashboard", wait_until="domcontentloaded", timeout=60000)
            print("   - Dashboard page loaded.")
            await asyncio.sleep(random.uniform(2, 4))

            time.sleep(15)

            # 2. Locate and search for the company
            print(f"🔍 Searching for company: '{COMPANY_TO_SEARCH}'...")
            search_input_selector = 'input[placeholder="Search company"]'
            search_input = page.locator(search_input_selector)
            
            await expect(search_input).to_be_visible(timeout=30000)
            
            await search_input.click()
            await search_input.type(COMPANY_TO_SEARCH, delay=random.uniform(100, 250))
            print(f"   - Typed '{COMPANY_TO_SEARCH}' into search bar.")

            wait_seconds = 3
            print(f"   - Waiting for {wait_seconds} seconds before pressing Enter...")
            time.sleep(15) # This is a blocking sleep
            
            await page.keyboard.press("Enter")
            print("   - 'Enter' key pressed.")

            time.sleep(15)

            # 3. Scrape data points
            print("💰 Scraping data points...")
            
            labels = page.locator("p.chakra-text.css-dhvn65")  # column names
            values = page.locator("span.chakra-text.css-esew9")  # values

            await expect(labels.first).to_be_visible(timeout=30000)
            
            count = await labels.count()
            print(f"   - Found {count} data points.")
            
            data = {}
            for i in range(count):
                key = await labels.nth(i).inner_text()
                val = await values.nth(i).inner_text()
                data[key] = val
            
            print("✅ Scraping successful!")
            print(json.dumps(data, indent=2))

            # --- NEW: UPDATE GOOGLE SHEET ---
            if data:
                print("\n🔄 Attempting to update Google Sheet...")
                # The GoogleSheetsClient's methods are synchronous, so we don't use 'await'.
                # It is initialized using settings from the .env file in the project root.
                gs_client = GoogleSheetsClient()
                success = gs_client.update_or_add_company_data(
                    company_name=COMPANY_TO_SEARCH,
                    data=data
                )
                if success:
                    print("✅ Google Sheet update process finished successfully.")
                else:
                    print("❌ Google Sheet update process failed. Check logs for errors.")
            else:
                print("⚠️ No data was scraped, skipping Google Sheet update.")
            # --- END OF NEW CODE ---


        except Exception as e:
            print(f"❌ An error occurred during the scraping process: {e}")
            await page.screenshot(path="scraping_error.png")
            print("   - A screenshot 'scraping_error.png' has been saved for debugging.")

        finally:
            print("\nClosing the browser in 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())