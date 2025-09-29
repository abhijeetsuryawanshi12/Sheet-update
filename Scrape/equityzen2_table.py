# Scrape/equityzen_funding_scrape.py
import asyncio
import json
import random
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
    Main function to run the EquityZen funding table scraping process.
    """
    target_url = f"https://equityzen.com/company/{COMPANY_URL_SLUG}/?tab=cap-table"

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
            print(f"🚀 Navigating to EquityZen page: {target_url}...")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            print("   - Page loaded.")

            # --- NEW: HANDLE CONFIRMATION POPUP ---
            try:
                print("   - Checking for confirmation popup...")
                # This selector finds a button that contains the text "Confirm", case-insensitively.
                confirm_button = page.locator('button:has-text("Confirm")')
                
                # Click the button only if it appears within 5 seconds.
                await confirm_button.click(timeout=5000)
                
                print("   - ✅ 'Confirm' button clicked.")
                # Wait a moment for the popup to close and content to stabilize
                await page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                # If the button doesn't appear, a timeout error occurs. We catch it and continue.
                print("   - Confirmation popup not found or not needed. Continuing...")
            # --- END OF NEW LOGIC ---

            table_container = page.locator("div.CompanyCapTable").first
            await expect(table_container).to_be_visible(timeout=30000)
            print("   - Funding table container is visible.")
            
            print("💰 Scraping table headers...")
            all_th_locators = table_container.locator("thead th.ant-table-cell")
            headers = []
            for i in range(await all_th_locators.count()):
                text = await all_th_locators.nth(i).inner_text()
                if text.strip(): 
                    headers.append(text.strip())
            
            print(f"   - Found headers: {headers}")

            print("💰 Scraping table rows...")
            row_locators = table_container.locator("tbody > tr.ant-table-row")
            row_count = await row_locators.count()
            
            if row_count == 0:
                print("❌ No data rows found in the table.")
                return

            print(f"   - Found {row_count} rows.")
            all_rows_data = []
            for i in range(row_count):
                row = row_locators.nth(i)
                all_td_locators = row.locator("td.ant-table-cell")
                cell_texts = []
                for j in range(await all_td_locators.count()):
                    cell_class = await all_td_locators.nth(j).get_attribute("class") or ""
                    if "ant-table-row-expand-icon-cell" not in cell_class:
                        text = await all_td_locators.nth(j).inner_text()
                        cell_texts.append(text.strip())
                
                if len(headers) == len(cell_texts):
                    row_data = dict(zip(headers, cell_texts))
                    all_rows_data.append(row_data)
                else:
                    print(f"   - WARNING: Row {i} has a mismatch between header count ({len(headers)}) and cell count ({len(cell_texts)}). Skipping row.")

            print("✅ Scraping successful!")
            print("--- Scraped Data ---")
            print(json.dumps(all_rows_data, indent=2))
            
            if all_rows_data:
                funding_history_json = json.dumps(all_rows_data)
                data_for_sheet = { "Funding History": funding_history_json }

                print("\n🔄 Attempting to update Google Sheet...")
                gs_client = GoogleSheetsClient()
                success = gs_client.update_or_add_company_data(
                    company_name=COMPANY_NAME,
                    data=data_for_sheet
                )
                if success:
                    print("✅ Google Sheet update process finished successfully.")
                else:
                    print("❌ Google Sheet update process failed. Check logs for errors.")

        except Exception as e:
            print(f"❌ An error occurred during the scraping process: {e}")
            await page.screenshot(path="equityzen_funding_error.png")
            print("   - A screenshot 'equityzen_funding_error.png' has been saved for debugging.")

        finally:
            print("\nClosing the browser in 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())