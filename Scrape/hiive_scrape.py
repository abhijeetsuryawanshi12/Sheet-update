# Scrape/hiive_scrape.py
import asyncio
import json
import random
import time
import sys
import os
from playwright.async_api import async_playwright, expect, TimeoutError

# --- Add parent directory to path to import 'app' modules ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.database import db_client

# --- Configuration ---
COOKIES_FILE_PATH = "Scrape/hiive_cookies.json"

def normalize_cookies(cookies_data):
    """
    Converts cookies from a browser-exported JSON file into the format
    required by Playwright's context.add_cookies() method.
    """
    normalized_cookies = []
    for cookie in cookies_data:
        same_site_mapping = {
            "no_restriction": "None", "unspecified": "None",
            "lax": "Lax", "strict": "Strict"
        }
        new_cookie = {
            "name": cookie["name"], "value": cookie["value"], "domain": cookie["domain"],
            "path": cookie["path"], "expires": cookie.get("expirationDate", -1),
            "httpOnly": cookie.get("httpOnly", False), "secure": cookie.get("secure", False),
            "sameSite": same_site_mapping.get(str(cookie.get("sameSite", "")).lower(), "Lax")
        }
        normalized_cookies.append(new_cookie)
    return normalized_cookies

async def scrape_company_data(page, company_name: str) -> dict | None:
    """
    Searches for a single company on Hiive and scrapes its market data.
    Returns a dictionary of the data or None if not found or an error occurs.
    """
    print(f"   - Searching for '{company_name}'...")
    try:
        search_input_selector = 'input[placeholder="Search company"]'
        search_input = page.locator(search_input_selector)
        
        await expect(search_input).to_be_visible(timeout=50000)
        await search_input.click()
        await search_input.fill("") # Clear previous search
        await search_input.type(company_name, delay=random.uniform(100, 200))
        
        await asyncio.sleep(random.uniform(2, 3)) # Wait for dropdown results
        await page.keyboard.press("Enter")
        print(f"   - Search submitted for '{company_name}'.")

        await page.wait_for_load_state('domcontentloaded', timeout=50000)
        await asyncio.sleep(random.uniform(2, 4)) # Extra wait for dynamic content

        # Check if company page loaded by looking for a key element
        header_locator = page.locator(f'h1:has-text("{company_name}")')
        try:
            await expect(header_locator).to_be_visible(timeout=50000)
        except TimeoutError:
            print(f"   - ❌ Could not confirm page for '{company_name}'. Company may not exist on Hiive. Skipping.")
            return None
        
        # Scrape data points
        labels = page.locator("p.chakra-text.css-dhvn65")
        values = page.locator("span.chakra-text.css-esew9")

        await expect(labels.first).to_be_visible(timeout=30000)
        
        count = await labels.count()
        if count == 0:
            print(f"   - ⚠️ No data points found for '{company_name}'.")
            return None
            
        data = {}
        # --- MODIFICATION: Only scrape the first two labels and values ---
        # Use min(2, count) to avoid errors if there are fewer than 2 results.
        for i in range(min(2, count)):
            key = (await labels.nth(i).inner_text()).strip()
            val = (await values.nth(i).inner_text()).strip()
            data[key] = val
        # --- END MODIFICATION ---
        
        print(f"   - ✅ Successfully scraped {len(data)} data points for '{company_name}'.")
        print(f"     Data: {data}")
        return data

    except TimeoutError as te:
        print(f"   - ❌ Timeout error while scraping '{company_name}': {te}")
        await page.screenshot(path=f"error_{company_name}.png")
        return None
    except Exception as e:
        print(f"   - ❌ An unexpected error occurred for '{company_name}': {e}")
        return None

async def main():
    """
    Main function to run the scraping process for all companies in the database.
    """
    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies = normalize_cookies(json.load(f))
        print(f"✅ Successfully loaded and normalized {len(cookies)} cookies.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Critical Error: Could not load cookies from '{COOKIES_FILE_PATH}'. {e}")
        return

    # --- Fetch companies from database ---
    print("\n--- INFO ---: Fetching company list from the database...")
    companies_to_scrape = db_client.get_all_company_names()
    if not companies_to_scrape:
        print("--- WARNING ---: No companies found in the database to scrape. Exiting.")
        db_client.close()
        return
    print(f"--- INFO ---: Found {len(companies_to_scrape)} companies to process.")
    # --- End fetch ---
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            print("🚀 Navigating to the Hiive dashboard...")
            await page.goto("https://app.hiive.com/dashboard", wait_until="domcontentloaded", timeout=60000)
            print("   - Dashboard loaded. Waiting for dynamic content...")
            await asyncio.sleep(5)

            for i, company_name in enumerate(companies_to_scrape):
                print(f"\n Scraping {i+1}/{len(companies_to_scrape)}: {company_name}")
                
                scraped_data = await scrape_company_data(page, company_name)
                
                if scraped_data:
                    highest_bid = scraped_data.get("HIGHEST BID")
                    lowest_ask = scraped_data.get("LOWEST ASK")
                    
                    if highest_bid or lowest_ask:
                        print(f"   - Data to update: Bid='{highest_bid}', Ask='{lowest_ask}'")
                        db_client.update_hiive_prices(company_name, highest_bid, lowest_ask)
                    else:
                        print("   - ⚠️ Scraped data did not contain 'Highest Bid' or 'Lowest Ask'.")
                
                # Add a random delay to be respectful to the server
                delay = random.uniform(5, 10)
                print(f"   - Waiting for {delay:.1f} seconds before next company...")
                await asyncio.sleep(delay)

        except Exception as e:
            print(f"❌ A critical error occurred during the main process: {e}")
            await page.screenshot(path="scraping_error_main.png")

        finally:
            print("\n✅ Scraping process finished.")
            await browser.close()
            db_client.close() # Close the database connection

if __name__ == "__main__":
    asyncio.run(main())