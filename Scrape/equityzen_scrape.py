# Scrape/equityzen_scraper.py
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

def create_url_slug(company_name: str) -> str:
    """
    Converts a company name like 'Cohesity, Inc.' to 'cohesity' or 'Digital Ocean' to 'digitalocean'.
    """
    clean_name = re.sub(r'[,.]?\s*(inc|llc|ltd|corp|corporation|com)\.?$', '', company_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'[.,]', '', clean_name)
    # Remove spaces instead of replacing with hyphens
    slug = clean_name.strip().lower().replace(' ', '')
    return slug

async def scrape_company_data(page, company_name, company_slug):
    """Scrapes Overview, Investors, Market Activity, and Funding Table for a single company."""
    about_url = f"https://equityzen.com/company/{company_slug}/"
    funding_url = f"{about_url}?tab=cap-table"
    scraped_data = {}

    try:
        # --- STAGE 1: Scrape "About" Page ---
        print(f"🚀 Navigating to {company_name}'s 'About' page...")
        await page.goto(about_url, wait_until="domcontentloaded", timeout=45000)

        page_title = await page.title()
        if "Sorry, we couldn't find that page" in page_title or "EquityZen | Invest in Private Companies" in page_title:
            print(f"❌ Page not found or redirected for {company_name}. Skipping.")
            return None

        # Handle confirmation popup
        try:
            await page.locator('button:has-text("Confirm")').click(timeout=5000)
            print("   - ✅ 'Confirm' button clicked.")
            await page.wait_for_load_state('networkidle', timeout=10000)
        except Exception:
            pass

        # Scrape Overview
        try:
            overview_locator = page.locator('div[class*="SvaSingleCompanyAboutCompanyTab--section"] div[class*="--description"]').first
            overview_text = await overview_locator.inner_text()
            scraped_data['Overview'] = overview_text.strip()
            print("   - Overview scraped.")
        except Exception:
            print(f"   - ⚠️ Overview not found for {company_name}.")

        # Scrape Investors
        try:
            investor_locators = page.locator('div[class*="Company-Investors"] a h5')
            investors = await investor_locators.all_inner_texts()
            if investors:
                scraped_data['Investors'] = ", ".join(investors)
                print("   - Investors scraped.")
        except Exception:
            print(f"   - ⚠️ Investors not found for {company_name}.")

        # Scrape Market Activity Card
        try:
            items_container = page.locator('div[class*="MarketActivityCard--items"]')
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

        # --- STAGE 2: Scrape Funding Table ---
        print(f"🚀 Navigating to {company_name}'s 'Funding' page...")
        await page.goto(funding_url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(5)
        table_container = page.locator("div.CompanyCapTable").first
        await expect(table_container).to_be_visible(timeout=30000)

        all_th = table_container.locator("thead th.ant-table-cell")
        headers = [text.strip() for text in await all_th.all_inner_texts() if text.strip()]
        
        row_locators = table_container.locator("tbody > tr.ant-table-row")
        if await row_locators.count() > 0:
            all_rows_data = []
            for i in range(await row_locators.count()):
                row = row_locators.nth(i)
                all_td = row.locator("td.ant-table-cell")
                cell_texts = []
                for j in range(await all_td.count()):
                    cell_class = await all_td.nth(j).get_attribute("class") or ""
                    if "ant-table-row-expand-icon-cell" not in cell_class:
                        cell_texts.append((await all_td.nth(j).inner_text()).strip())
                if len(headers) == len(cell_texts):
                    all_rows_data.append(dict(zip(headers, cell_texts)))
            scraped_data['Funding History'] = json.dumps(all_rows_data)
            print("   - Funding History scraped.")

        return scraped_data

    except Exception as e:
        print(f"❌ An error occurred while scraping {company_name}: {e}")
        await page.screenshot(path=f"error_{company_slug}.png")
        return None


async def main():
    gs_client = GoogleSheetsClient()
    db_client = DatabaseClient()
    companies_to_scrape = gs_client.get_company_list()

    if not companies_to_scrape:
        print("❌ No companies found in the Google Sheet. Exiting.")
        return

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

        start_index = 40
        
        # We slice the list to start from the desired index.
        companies_to_process = companies_to_scrape[start_index:]

        for i, company_name in enumerate(companies_to_process):

            original_index = i + start_index
            print("-" * 50)
            print(f"Processing company {i+1}/{len(companies_to_process)}: {company_name}")

            company_slug = create_url_slug(company_name)
            all_data = await scrape_company_data(page, company_name, company_slug)
            
            if all_data:
                print(f"   - ✅ Scraping successful for {company_name}. Updating stores...")
                db_client.update_scraped_data(company_name=company_name, data=all_data)
                gs_client.update_or_add_company_data(company_name=company_name, data=all_data)
            else:
                print(f"   - ❌ No data scraped for {company_name}. Not updating stores.")

            sleep_duration = random.uniform(5, 12)
            print(f"--- Pausing for {sleep_duration:.2f} seconds before next company ---")
            time.sleep(sleep_duration)

        await browser.close()
        db_client.close()
        print("\n✅ All companies processed.")

if __name__ == "__main__":
    asyncio.run(main())