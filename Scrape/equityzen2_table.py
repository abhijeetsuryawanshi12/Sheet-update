# Scrape/equityzen_funding_scrape.py
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

# --- Configuration ---
COOKIES_FILE_PATH = "Scrape/equityzen_cookies.json"

def normalize_cookies(cookies_data):
    """Converts browser-exported cookies to the format Playwright requires."""
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

def create_url_slug(company_name: str) -> str:
    """
    Converts a company name like 'Cohesity, Inc.' to a URL-friendly slug like 'cohesity'.
    """
    # 1. Remove common corporate suffixes, punctuation, and extra spaces
    # This regex looks for common suffixes preceded by a comma or space and makes them optional.
    # It handles cases like ", Inc.", " Inc.", ".com", etc.
    clean_name = re.sub(r'[,.]?\s*(inc|llc|ltd|corp|corporation|com)\.?$', '', company_name, flags=re.IGNORECASE)
    
    # 2. Remove any remaining punctuation like commas or periods.
    clean_name = re.sub(r'[.,]', '', clean_name)

    # 3. Convert to lowercase and replace spaces with hyphens
    slug = clean_name.strip().lower().replace(' ', '-')
    
    return slug


async def scrape_company_funding_table(page, company_name, company_slug):
    """Scrapes the funding table for a single company."""
    target_url = f"https://equityzen.com/company/{company_slug}/?tab=cap-table"
    print(f"🚀 Navigating to {company_name}'s page: {target_url}...")
    
    try:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
        
        page_title = await page.title()
        if "Sorry, we couldn't find that page" in page_title or "EquityZen | Invest in Private Companies" in page_title:
            print(f"❌ Page not found or redirected for {company_name}. Skipping.")
            return None

        try:
            confirm_button = page.locator('button:has-text("Confirm")')
            await confirm_button.click(timeout=5000)
            print("   - ✅ 'Confirm' button clicked.")
            await page.wait_for_load_state('networkidle', timeout=10000)
        except Exception:
            pass

        table_container = page.locator("div.CompanyCapTable").first
        await expect(table_container).to_be_visible(timeout=30000)

        all_th_locators = table_container.locator("thead th.ant-table-cell")
        headers = [text.strip() for text in await all_th_locators.all_inner_texts() if text.strip()]

        row_locators = table_container.locator("tbody > tr.ant-table-row")
        row_count = await row_locators.count()
        if row_count == 0:
            print(f"   - ⚠️ No data rows found in the table for {company_name}.")
            return None

        all_rows_data = []
        for i in range(row_count):
            row = row_locators.nth(i)
            all_td_locators = row.locator("td.ant-table-cell")
            cell_texts = []
            for j in range(await all_td_locators.count()):
                cell_class = await all_td_locators.nth(j).get_attribute("class") or ""
                if "ant-table-row-expand-icon-cell" not in cell_class:
                    cell_texts.append((await all_td_locators.nth(j).inner_text()).strip())
            
            if len(headers) == len(cell_texts):
                all_rows_data.append(dict(zip(headers, cell_texts)))
            else:
                print(f"   - WARNING: Row {i} for {company_name} has a header/cell count mismatch. Skipping row.")
        
        return all_rows_data

    except Exception as e:
        print(f"❌ An error occurred while scraping {company_name}: {e}")
        await page.screenshot(path=f"error_{company_slug}.png")
        print(f"   - A screenshot 'error_{company_slug}.png' has been saved.")
        return None


async def main():
    """Main function to orchestrate the scraping of all companies from the Google Sheet."""
    gs_client = GoogleSheetsClient()
    companies_to_scrape = gs_client.get_company_list()

    if not companies_to_scrape:
        print("❌ No companies found in the Google Sheet. Exiting.")
        return

    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies = normalize_cookies(json.load(f))
        print(f"✅ Successfully loaded and normalized {len(cookies)} cookies.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error with cookie file: {e}")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        for i, company_name in enumerate(companies_to_scrape):
            print("-" * 50)
            print(f"Processing company {i+1}/{len(companies_to_scrape)}: {company_name}")
            
            company_slug = create_url_slug(company_name)
            
            funding_data = await scrape_company_funding_table(page, company_name, company_slug)
            
            if funding_data:
                funding_history_json = json.dumps(funding_data)
                data_for_sheet = {"Funding History": funding_history_json}
                
                print(f"   - ✅ Scraping successful for {company_name}. Updating sheet...")
                gs_client.update_or_add_company_data(
                    company_name=company_name,
                    data=data_for_sheet
                )
            else:
                print(f"   - ❌ No data scraped for {company_name}. Not updating sheet.")

            sleep_duration = random.uniform(5, 12)
            print(f"--- Pausing for {sleep_duration:.2f} seconds before next company ---")
            time.sleep(sleep_duration)

        print("-" * 50)
        print("✅ All companies processed. Closing browser.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())