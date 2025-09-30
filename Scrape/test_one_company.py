import asyncio
import json
import random
import sys
import os
import time
import re

from playwright.async_api import async_playwright, expect

# --- Add parent directory to path to import 'app' modules ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.google_sheets import GoogleSheetsClient
from app.services.database import DatabaseClient

# --- Configuration ---
COOKIES_FILE_PATH = "Scrape/equityzen_cookies.json"

def normalize_cookies(cookies_data):
    """Converts browser-exported cookies to the format Playwright requires."""
    normalized_cookies = []
    for cookie in cookies_data:
        same_site_mapping = { "no_restriction": "None", "unspecified": "None", "lax": "Lax", "strict": "Strict" }
        new_cookie = {
            "name": cookie["name"], "value": cookie["value"], "domain": cookie["domain"], "path": cookie["path"],
            "expires": cookie.get("expirationDate", -1), "httpOnly": cookie.get("httpOnly", False),
            "secure": cookie.get("secure", False), "sameSite": same_site_mapping.get(str(cookie.get("sameSite", "")).lower(), "Lax")
        }
        normalized_cookies.append(new_cookie)
    return normalized_cookies

async def scrape_company_data(page, company_name):
    """Searches for a company, navigates to its page, and scrapes its profile and funding data."""
    scraped_data = {}
    overview_section_locator = page.locator('div[class*="SvaSingleCompanyAboutCompanyTab--section"]').first

    # --- STAGE 1: Search and Navigate ---
    try:
        # Start at the required /welcome page.
        print(f"🚀 Navigating to the '/welcome' page as the starting point...")
        await page.goto("https://equityzen.com/welcome/", wait_until="domcontentloaded", timeout=45000)

        # Click the 'Investments' link to navigate to the page with the search bar.
        print("   - Clicking 'Investments' link to access the main search functionality...")
        investments_link = page.get_by_role("link", name="Investments", exact=True)
        await expect(investments_link).to_be_visible(timeout=15000)
        await investments_link.click()

        time.sleep(3)
        
        # Now that we are on the correct page, find and use the search bar.
        print("   - Waiting for the investments page and search bar to load...")
        search_input = page.get_by_placeholder("Search")
        await expect(search_input).to_be_visible(timeout=15000)

        print(f"   - Typing '{company_name}' into the search bar.")
        await search_input.press_sequentially(company_name, delay=random.randint(50, 150))

        time.sleep(3)

        first_result_selector = 'div[class*="SearchDropdown-item"]'
        await expect(page.locator(first_result_selector).first).to_be_visible(timeout=10000)

        print("   - Search results found. Clicking the first one.")
        await page.locator(first_result_selector).first.click()

        print("   - Waiting for company page to load...")
        await expect(overview_section_locator).to_be_visible(timeout=30000)
        print(f"   - Successfully navigated to {company_name}'s page.")

    except Exception as e:
        print(f"❌ Failed to search and navigate for '{company_name}'. It might not exist. Error: {e}")
        return None

    try:
        # Handle confirmation popup if it appears after navigation
        try:
            await page.locator('button:has-text("Confirm")').click(timeout=5000)
            print("   - ✅ 'Confirm' button clicked.")
            await expect(overview_section_locator).to_be_visible(timeout=10000)
        except Exception:
            pass # Popup might not be there, which is fine

        # --- STAGE 2: Scrape "About" Tab Data ---
        print("🚀 Scraping 'About' tab data...")
        # Scrape Overview
        try:
            overview_text = await overview_section_locator.locator('div[class*="--description"]').inner_text(timeout=10000)
            scraped_data['Overview'] = overview_text.strip()
            print("   - Overview scraped.")
        except Exception:
            print(f"   - ⚠️ Overview not found for {company_name}.")

        # Scrape Investors
        try:
            investor_locators = page.locator('div[class*="Company-Investors"] a h5')
            if await investor_locators.count() > 0:
                 investors = await investor_locators.all_inner_texts()
                 scraped_data['Investors'] = ", ".join(investors)
                 print("   - Investors scraped.")
        except Exception:
            print(f"   - ⚠️ Investors not found for {company_name}.")

        # Scrape Market Activity Card
        try:
            items_container = page.locator('div[class*="MarketActivityCard--items"]')
            await expect(items_container).to_be_visible(timeout=5000)
            all_items = items_container.locator('div[class*="MarketActivityCard--item"]')
            for i in range(await all_items.count()):
                item = all_items.nth(i)
                if await item.locator('div[class*="--item-label"]').count() > 0:
                    label = await item.locator('div[class*="--item-label"]').inner_text()
                    value = await item.locator('div[class*="--item-value"]').inner_text()
                    if label and value and value != '--':
                        scraped_data[label.strip()] = value.strip()
            print("   - Market Activity scraped.")
        except Exception:
            print(f"   - ⚠️ Market Activity card not found for {company_name}.")

        # --- STAGE 3: Scrape Funding Table ---
        try:
            print("🚀 Navigating to 'Cap Table' tab...")
            await page.locator('div[role="tab"]:has-text("Cap Table")').click(timeout=10000)
            await page.wait_for_selector("div.CompanyCapTable, div.CompanyCapTable-funding-history-container", timeout=20000)
        except Exception as e:
            print(f"   - ❌ Could not find or click 'Cap Table' tab. Skipping funding history. Error: {e}")
            return scraped_data

        funding_scraped = False
        # Attempt 1: Modern Ant Design Table
        try:
            table_container = page.locator("div.CompanyCapTable").first
            row_locators = table_container.locator("tbody > tr.ant-table-row")
            if await row_locators.count(timeout=5000) > 0:
                all_th = table_container.locator("thead th.ant-table-cell")
                headers = [text.strip() for text in await all_th.all_inner_texts() if text.strip()]
                all_rows_data = []
                for i in range(await row_locators.count()):
                    row = row_locators.nth(i)
                    all_td = row.locator("td.ant-table-cell")
                    cell_texts = [
                        (await all_td.nth(j).inner_text()).strip()
                        for j in range(await all_td.count())
                        if "ant-table-row-expand-icon-cell" not in (await all_td.nth(j).get_attribute("class") or "")
                    ]
                    if len(headers) == len(cell_texts):
                        all_rows_data.append(dict(zip(headers, cell_texts)))
                if all_rows_data:
                    scraped_data['Funding History'] = json.dumps(all_rows_data)
                    print("   - ✅ Funding History scraped using Method 1 (Ant Design Table).")
                    funding_scraped = True
        except Exception:
            print("   - ℹ️ Method 1 for funding table failed or found no data. Trying fallback.")

        # Attempt 2: Simple Two-Column Table (Fallback)
        if not funding_scraped:
            try:
                simple_table = page.locator("div.CompanyCapTable-funding-history-container table").first
                rows = simple_table.locator("tbody > tr.ant-table-row")
                if await rows.count(timeout=5000) > 0:
                    all_rows_data = []
                    headers = ["Date", "Price per Share"]
                    for i in range(await rows.count()):
                        cells = await rows.nth(i).locator("td.ant-table-cell").all_inner_texts()
                        if len(cells) == 2:
                            all_rows_data.append(dict(zip(headers, [cell.strip() for cell in cells])))
                    if all_rows_data:
                        scraped_data['Funding History'] = json.dumps(all_rows_data)
                        print("   - ✅ Funding History scraped using Method 2 (Simple Table).")
                        funding_scraped = True
            except Exception:
                print("   - ⚠️ Method 2 for funding table also failed.")

        if not funding_scraped:
             print(f"   - ❌ Could not scrape Funding History for {company_name}.")

        return scraped_data

    except Exception as e:
        print(f"❌ An error occurred while scraping data for {company_name}: {e}")
        slug_for_error = re.sub(r'[^a-z0-9]+', '-', company_name.lower())
        await page.screenshot(path=f"error_{slug_for_error}.png")
        return scraped_data

async def main():
    gs_client = GoogleSheetsClient()
    db_client = DatabaseClient()

    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies = normalize_cookies(json.load(f))
    except Exception as e:
        print(f"❌ Error with cookie file: {e}")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        await context.add_cookies(cookies)
        page = await context.new_page()

        company_to_scrape = "Lambda"

        print("-" * 50)
        print(f"Processing single company: {company_to_scrape}")

        all_data = await scrape_company_data(page, company_to_scrape)
        
        if all_data:
            print(f"   - ✅ Scraping successful for {company_to_scrape}. Updating stores...")
            db_client.update_scraped_data(company_name=company_to_scrape, data=all_data)
            gs_client.update_or_add_company_data(company_name=company_to_scrape, data=all_data)
        else:
            print(f"   - ❌ No data scraped for {company_to_scrape}. Not updating stores.")
        
        await browser.close()
        db_client.close()
        print("\n✅ Script finished.")

if __name__ == "__main__":
    asyncio.run(main())